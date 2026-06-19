import random
import time


def get_all_items(sp, playlist_id, total):
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


def list_contributors(items):
    """Return contributors sorted by song count, descending.

    Each entry is ``{"id": user_id, "count": int}``.
    """
    counts: dict[str, int] = {}
    for x in items:
        uid = x["added_by"]["id"]
        counts[uid] = counts.get(uid, 0) + 1
    return [
        {"id": uid, "count": n}
        for uid, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]


def _bucket_by_user(items):
    by_user: dict[str, list] = {}
    for x in items:
        uid = x["added_by"]["id"]
        by_user.setdefault(uid, []).append(x)
    return by_user


def _songunique(items):
    return [x["track"]["name"] for x in items]


def _find_nearest_free(reserved, ideal, length):
    ideal = max(0, min(length - 1, ideal))
    if ideal not in reserved:
        return ideal
    for offset in range(1, length):
        for cand in (ideal - offset, ideal + offset):
            if 0 <= cand < length and cand not in reserved:
                return cand
    raise ValueError("No free slot in playlist")


def _build_order(by_user, main_users, guest_users, length):
    """Build the target ordering of track names.

    Guests get their songs placed at evenly-spaced reserved positions
    (collisions resolved to the nearest free slot, processing larger guests
    first since their positions are most constrained). Remaining slots are
    filled by round-robin among the main contributors.
    """
    order: list[str | None] = [None] * length
    reserved: dict[int, str] = {}

    sorted_guests = sorted(
        guest_users, key=lambda u: -len(by_user.get(u, []))
    )
    for uid in sorted_guests:
        songs = list(by_user.get(uid, []))
        n = len(songs)
        if n == 0:
            continue
        random.shuffle(songs)
        for i, song in enumerate(songs):
            ideal = int((i + 0.5) * length / n)
            slot = _find_nearest_free(reserved, ideal, length)
            reserved[slot] = song["track"]["name"]

    for slot, name in reserved.items():
        order[slot] = name

    remaining = [u for u in main_users if by_user.get(u)]
    main_buckets = {u: list(by_user[u]) for u in remaining}
    position = 0
    for slot in range(length):
        if order[slot] is not None:
            continue
        if not remaining:
            break
        if position > len(remaining) - 1:
            position = 0
        uid = remaining[position]
        bucket = main_buckets[uid]
        pick = random.randrange(len(bucket))
        song = bucket.pop(pick)
        order[slot] = song["track"]["name"]
        if not bucket:
            del main_buckets[uid]
            remaining.pop(position)
        else:
            position += 1

    return [name for name in order if name is not None]


def shuffle_playlist(sp, playlist_id, guests=None, log=print):
    """Reorder ``playlist_id`` round-robin by contributor.

    ``sp`` is an authenticated ``spotipy.Spotify`` client whose user owns
    (or is a collaborator on) the playlist. ``log`` receives human-readable
    progress strings.

    ``guests`` is an optional iterable of user IDs whose songs should be
    sprinkled at evenly-spaced positions throughout the playlist instead of
    being round-robin'd alongside the main contributors. A guest with ``g``
    songs in an ``N``-track playlist gets a song placed roughly every
    ``N / g`` slots.
    """
    guest_set = set(guests) if guests else set()

    meta = sp.playlist(playlist_id, fields="name,snapshot_id")
    log(f"Loaded playlist: {meta['name']}")

    total = sp.playlist_tracks(playlist_id, fields="total")["total"]
    log(f"Total tracks: {total}")

    items = get_all_items(sp, playlist_id, total)
    log(f"Fetched {len(items)} items")

    by_user = _bucket_by_user(items)
    main_users = [uid for uid in by_user if uid not in guest_set]
    guest_users = [uid for uid in by_user if uid in guest_set]
    random.shuffle(main_users)

    log(
        f"{len(main_users)} main contributor(s), "
        f"{len(guest_users)} guest(s)"
    )

    order = _build_order(by_user, main_users, guest_users, total)
    log(f"Built target order of {len(order)} tracks")

    for i, next_song in enumerate(order):
        current = _songunique(get_all_items(sp, playlist_id, total))
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
