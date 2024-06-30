import spotipy
import random
import time
from spotipy.oauth2 import SpotifyOAuth

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id="49cf4af08d524778ac017e8ec64da9ce",
                                               client_secret="3a007a13728a401f876b3075b4cbee6f",
                                               redirect_uri="https://github.com/quinnal2/WujuBot",
                                               scope="playlist-modify-public"), requests_timeout=10, retries=10)


wuju_uri = "6yaoKUTEdAe7kHpMawOePi" #unique id of the wuju

results = sp.playlist(wuju_uri, fields=None) #only pulls the first 100 songs, only useful for playlist name

print(results['name'])

playlistlength = sp.playlist_tracks(wuju_uri, fields= None)['total']        #detects total playlist length

def getAllItems():
    items = []
    offset = 0

    # get all playlist items regardless of length of playlist
    while offset < playlistlength:
        next100Items = sp.playlist_items(wuju_uri, fields= None, offset= offset)['items']
        items = items + next100Items
        offset += 100
    return items

itemitems = getAllItems()

def userunique(list1):      #gets the number of unique users who have added to the playlist
    
    unique_list = []

    for x in list1:
        if x['added_by']['id'] not in unique_list:
            unique_list.append(x['added_by']['id'])

    return(unique_list)



def songunique(list1):      #gets the name of every song on the playlist in order
    
    unique_list = []

    for x in list1:
        unique_list.append(x['track']['name'])
    
    return(unique_list)



def idsongunique(list1):    #gets the id of every song on the playlist in order
    
    unique_list = []

    for x in list1:
        unique_list.append(x['track']['id'])
    
    return(unique_list)



songlist = songunique(itemitems)        #not used
individuals = userunique(itemitems)     #used
random.shuffle(individuals)         #shuffles the order of the users
idsonglist = idsongunique(itemitems)    #not used

#print("Total number of Individuals:", len(individuals))
#print(individuals)
#print(songlist)



def usersongs(list1, user):             #adds all songs by a given user to a list
    songorder = []

    for x in list1:
        if x['added_by']['id'] == user:
            songorder.append(x)
    
    return songorder


def combinedlist(list1, users):         #combines the lists of each users songs into a dictionary
    songs_by_user = {}

    for x in users:
        songs_by_user[x] = usersongs(list1, x)
    
    return songs_by_user

complete_list = combinedlist(itemitems, individuals)

def ordermaker(list1, users, length):   #creates a list of randomly sorted songs, alternating by user
    order = []
    position = 0

    for x in range(length):
        if position > len(users)-1:       #this seems to not reset the position if it passes the number of users
            position = 0

        thepick = random.randrange(len(list1[users[position]]))     #bitch
        order.append(list1[users[position]][thepick]['track']['name'])    #adds the picked song
        list1[users[position]].remove(list1[users[position]][thepick])

        if len(list1[users[position]]) == 0:
            del list1[users[position]]
            users.remove(users[position])
        else:
             position += 1 #advances the position
        
    return order

order = ordermaker(complete_list, individuals, playlistlength)
print(order)

playlistSnapshotId = results['snapshot_id']

for i, nextSongInOrder in enumerate(order):
    currentSongOrder = songunique(getAllItems()) # get updated order of songs from current playlist
    for j, songInCurrentPlaylist in enumerate(currentSongOrder):
        if nextSongInOrder == songInCurrentPlaylist:
            print('Current song: ' + nextSongInOrder)
            print('Position: ' + str(i))
            sp.playlist_reorder_items(playlist_id = wuju_uri, range_start = j, insert_before = i, snapshot_id = None)
            time.sleep(1)
            break # exit loop since we found the song