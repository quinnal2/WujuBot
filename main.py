import spotipy
import random
from spotipy.oauth2 import SpotifyOAuth

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id="49cf4af08d524778ac017e8ec64da9ce",
                                               client_secret="3a007a13728a401f876b3075b4cbee6f",
                                               redirect_uri="https://github.com/quinnal2/WujuBot",
                                               scope="user-library-read"))


wuju_uri = "6yaoKUTEdAe7kHpMawOePi" #unique id of the wuju

results = sp.playlist(wuju_uri, fields=None) #only pulls the first 100 songs, only useful for playlist name

print(results['name'])

itemresults = sp.playlist_items(wuju_uri, fields= None)['items']                     #only pulls first 100 songs
itemresults2 = sp.playlist_items(wuju_uri, fields= None, offset=100)['items']        #pulls songs starting after the first results, need better way incase playlist longer than 200
itemitems = itemresults + itemresults2
playlistlength = sp.playlist_tracks(wuju_uri, fields= None)['total']        #detects total playlist length


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
        if position > len(users):       #this seems to not reset the position if it passes the number of users
            position == 0

        thepick = random.randrange(len(list1[users[position]]))     #bitch

        if list1[individuals[position]][thepick]['track']['name'] not in order:     #checks if the picked song is already added
            order.append(list1[individuals[position]][thepick]['track']['name'])    #adds the picked song
            position += 1                                                           #advances the position
        
    return order

order = ordermaker(complete_list, individuals, playlistlength)

print(order)