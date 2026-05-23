import random
import time


def _get_all_items(sp, playlist_id, total):
    items = []
    offset = 0
    while offset < total:
        next_items = sp.playlist_items(
            playlist_id, fields=None, limit=100, offset=offset
        )["items"]
        if not next_items:
            break
        items.extend(next_items)
        offset += len(next_items)
    return items


def _userunique(items):
    unique = []
    for x in items:
        uid = x["added_by"]["id"]
        if uid not in unique:
            unique.append(uid)
    return unique


def _songunique(items):
    return [x["track"]["name"] for x in items]


def _combinedlist(items, users):
    by_user = {u: [] for u in users}
    for x in items:
        uid = x["added_by"]["id"]
        if uid in by_user:
            by_user[uid].append(x)
    return by_user


def _ordermaker(by_user, users, length):
    order = []
    position = 0
    for _ in range(length):
        if not users:
            break
        if position > len(users) - 1:
            position = 0

        user = users[position]
        bucket = by_user[user]
        pick = random.randrange(len(bucket))
        order.append(bucket[pick]["track"]["name"])
        bucket.pop(pick)

        if len(bucket) == 0:
            del by_user[user]
            users.pop(position)
        else:
            position += 1
    return order


def shuffle_playlist(sp, playlist_id, log=print):
    """Reorder ``playlist_id`` round-robin by contributor.

    ``sp`` is an authenticated ``spotipy.Spotify`` client whose user owns the
    playlist (or has write access). ``log`` receives human-readable progress
    strings; pass ``st.write`` from Streamlit, or leave as ``print`` for CLI.
    """
    meta = sp.playlist(playlist_id, fields="name,snapshot_id")
    log(f"Loaded playlist: {meta['name']}")

    total = sp.playlist_tracks(playlist_id, fields="total")["total"]
    log(f"Total tracks: {total}")

    items = _get_all_items(sp, playlist_id, total)
    log(f"Fetched {len(items)} items")

    users = _userunique(items)
    random.shuffle(users)
    log(f"Found {len(users)} unique contributors")

    by_user = _combinedlist(items, users)
    order = _ordermaker(by_user, list(users), total)
    log(f"Built target order of {len(order)} tracks")

    for i, next_song in enumerate(order):
        current = _songunique(_get_all_items(sp, playlist_id, total))
        for j, song in enumerate(current):
            if next_song == song:
                log(f"[{i + 1}/{len(order)}] Moving '{next_song}' from {j} to {i}")
                sp.playlist_reorder_items(
                    playlist_id=playlist_id,
                    range_start=j,
                    insert_before=i,
                )
                time.sleep(1)
                break

    log("Shuffle complete.")
    return order
