import re

import spotipy
import streamlit as st
from spotipy.cache_handler import CacheHandler
from spotipy.oauth2 import SpotifyOAuth

from shuffle import get_all_items, list_contributors, shuffle_playlist

PLAYLIST_ID_RE = re.compile(r"playlist[/:]([A-Za-z0-9]+)")
TOKEN_KEY = "spotify_token_info"
LOADED_KEY = "loaded_playlist"
GUEST_KEY_PREFIX = "guest_"


class SessionCacheHandler(CacheHandler):
    """Stores the Spotify token in ``st.session_state`` so each browser session
    has its own isolated token (no shared on-disk ``.cache`` file)."""

    def get_cached_token(self):
        return st.session_state.get(TOKEN_KEY)

    def save_token_to_cache(self, token_info):
        st.session_state[TOKEN_KEY] = token_info


def make_oauth() -> SpotifyOAuth:
    return SpotifyOAuth(
        client_id=st.secrets["SPOTIFY_CLIENT_ID"],
        client_secret=st.secrets["SPOTIFY_CLIENT_SECRET"],
        redirect_uri=st.secrets["REDIRECT_URI"],
        scope="playlist-modify-public playlist-modify-private",
        cache_handler=SessionCacheHandler(),
        show_dialog=True,
    )


def extract_playlist_id(url_or_id: str) -> str | None:
    s = url_or_id.strip()
    if not s:
        return None
    match = PLAYLIST_ID_RE.search(s)
    if match:
        return match.group(1)
    if re.fullmatch(r"[A-Za-z0-9]+", s):
        return s
    return None


def load_playlist(sp: spotipy.Spotify, playlist_id: str) -> dict:
    """Fetch playlist metadata + contributor list with display names."""
    meta = sp.playlist(playlist_id, fields="name")
    total = sp.playlist_tracks(playlist_id, fields="total")["total"]
    items = get_all_items(sp, playlist_id, total)

    enriched = []
    for entry in list_contributors(items):
        uid = entry["id"]
        try:
            user = sp.user(uid)
            name = user.get("display_name") or uid
        except spotipy.SpotifyException:
            name = uid
        enriched.append({"id": uid, "name": name, "count": entry["count"]})

    return {
        "playlist_id": playlist_id,
        "name": meta["name"],
        "total": total,
        "contributors": enriched,
    }


def clear_loaded_state() -> None:
    st.session_state.pop(LOADED_KEY, None)
    for key in [
        k for k in list(st.session_state.keys())
        if isinstance(k, str) and k.startswith(GUEST_KEY_PREFIX)
    ]:
        del st.session_state[key]


def main() -> None:
    st.set_page_config(page_title="WujuBot", page_icon=None, layout="centered")
    st.title("WujuBot")
    st.caption("Round-robin shuffle a Spotify playlist by contributor.")

    oauth = make_oauth()

    qp = st.query_params
    if "code" in qp and not oauth.validate_token(oauth.get_cached_token()):
        try:
            oauth.get_access_token(qp["code"], as_dict=False, check_cache=False)
        except Exception as exc:
            st.error(f"Spotify rejected the login: {exc}")
            st.stop()
        st.query_params.clear()
        st.rerun()

    token_info = oauth.validate_token(oauth.get_cached_token())
    if not token_info:
        auth_url = oauth.get_authorize_url()
        st.markdown(
            "You'll be sent to Spotify to authorize, then bounced back here."
        )
        st.link_button("Login with Spotify", auth_url)
        st.stop()

    sp = spotipy.Spotify(auth_manager=oauth, requests_timeout=10, retries=10)

    try:
        me = sp.current_user()
        st.success(f"Signed in as {me.get('display_name') or me['id']}")
    except spotipy.SpotifyException as exc:
        st.error(f"Could not load your Spotify profile: {exc}")
        if st.button("Log out"):
            st.session_state.pop(TOKEN_KEY, None)
            st.rerun()
        st.stop()

    with st.sidebar:
        if st.button("Log out"):
            st.session_state.pop(TOKEN_KEY, None)
            st.rerun()

    url = st.text_input(
        "Playlist URL",
        placeholder="https://open.spotify.com/playlist/...",
        help="Paste a Spotify playlist link, or just the playlist ID.",
    )

    if st.button("Load contributors", disabled=not url):
        playlist_id = extract_playlist_id(url)
        if not playlist_id:
            st.error("Could not parse a playlist ID from that input.")
            st.stop()
        try:
            with st.spinner("Loading playlist..."):
                loaded = load_playlist(sp, playlist_id)
        except spotipy.SpotifyException as exc:
            st.error(f"Spotify error loading playlist: {exc}")
            st.stop()
        clear_loaded_state()
        st.session_state[LOADED_KEY] = loaded
        st.rerun()

    loaded = st.session_state.get(LOADED_KEY)
    if not loaded:
        return

    st.divider()
    st.subheader(loaded["name"])
    st.caption(
        f"{loaded['total']} tracks, {len(loaded['contributors'])} contributor(s)"
    )

    st.markdown(
        "**Mark guests** below. A guest's songs are sprinkled at evenly "
        "spaced positions through the playlist (a guest with 10 songs in a "
        "100-track playlist gets one slot every 10). Everyone else "
        "round-robins as before."
    )

    for c in loaded["contributors"]:
        plural = "song" if c["count"] == 1 else "songs"
        st.checkbox(
            f"{c['name']} \u2014 {c['count']} {plural}",
            key=f"{GUEST_KEY_PREFIX}{c['id']}",
        )

    col_shuffle, col_reset = st.columns([3, 1])
    with col_shuffle:
        shuffle_clicked = st.button(
            "Shuffle", type="primary", use_container_width=True
        )
    with col_reset:
        if st.button("Reset", use_container_width=True):
            clear_loaded_state()
            st.rerun()

    if not shuffle_clicked:
        return

    guest_ids = {
        c["id"] for c in loaded["contributors"]
        if st.session_state.get(f"{GUEST_KEY_PREFIX}{c['id']}", False)
    }

    with st.status("Shuffling...", expanded=True) as status:
        log_box = st.empty()
        log_lines: list[str] = []

        def log(msg) -> None:
            log_lines.insert(0, str(msg))
            with log_box.container(height=320, border=True):
                for line in log_lines:
                    st.text(line)

        try:
            shuffle_playlist(
                sp,
                loaded["playlist_id"],
                guests=guest_ids,
                log=log,
            )
        except spotipy.SpotifyException as exc:
            if exc.http_status == 403:
                status.update(label="Permission denied", state="error")
                st.error(
                    "Spotify returned 403. You can only reorder playlists "
                    "you own or are a collaborator on."
                )
            else:
                status.update(label="Spotify error", state="error")
                st.error(f"Spotify error: {exc}")
            st.stop()
        except Exception as exc:
            status.update(label="Failed", state="error")
            st.exception(exc)
            st.stop()

        status.update(label="Shuffle complete", state="complete")

    st.success("Done. Reload the playlist in Spotify to see the new order.")


if __name__ == "__main__":
    main()
