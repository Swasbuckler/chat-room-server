from flask import Flask, request
from flask_cors import CORS
from flask_socketio import join_room, leave_room, emit, disconnect, SocketIO
import random
from string import ascii_uppercase
import numbers
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask( __name__ )
app.config[ 'SECRET_KEY' ] = os.getenv( 'SECRET_KEY' )
CORS( app, origins=os.getenv('FRONTEND_URL'), methods=[ 'POST', 'GET' ] )
socketio = SocketIO( app, cors_allowed_origins=os.getenv('FRONTEND_URL') )

existing_rooms = {}

def generate_unique_code( length ):

  while True:
    code = ''
    for _ in range( length ):
      code += random.choice( ascii_uppercase )

    if code not in existing_rooms:
      break

  return code

@app.route( '/', methods=[ 'POST', 'GET' ] )
def home():

  return 'Server is Running'

@app.route( '/search', methods=[ 'POST', 'GET' ] )
def search():

  if request.method == 'POST':
    name = ''
    code = ''
    isJoin = True

    try:
      name = request.json[ 'name' ].strip()
      code = request.json[ 'code' ]
      isJoin = request.json[ 'isJoin' ]

    except:
      return { 'success': False, 'reason': 'Improper / Incorrect data Given' }

    if not name:
      return { 'success': False, 'reason': 'Username was not Given' }
    
    if isJoin and not code:
      return { 'success': False, 'reason': 'Room Code was not Given to Join' }

    room = code
   
    if not isJoin:
      room = generate_unique_code( 4 )
      existing_rooms[room] = { 
        'members': [],
        'messages': [],
      }

    elif code not in existing_rooms:
      return { 'success': False, 'reason': 'Room has not been Created' }
    
    if ( next((member for member in existing_rooms[room]['members'] if member['name'] == name), None) ):
      return { 'success': False, 'reason': 'Username already exists. Enter a different Username' }

    return { 
      'success': True, 
      'data': { 
        'name': name,
        'room': room,
      } 
    }

@app.route( '/room', methods=[ 'POST', 'GET' ] )
def room():

  if request.method == 'POST':
    room = ''

    try:
      room = request.json[ 'room' ]
    
    except:
      return { 'success': False }

    if room not in existing_rooms:
      return { 'success': False }

    return { 'success': True }

@socketio.on( 'connect' )
def connection( auth ):
  name = ''
  room = ''

  try:
    name = auth[ 'name' ]
    room = auth[ 'room' ]

  except:
    disconnect()
    return

  if not name:
    disconnect()
    return

  if room not in existing_rooms:
    leave_room( room )
    disconnect()
    return

  join_room( room )
  existing_rooms[room]['messages'].append( { 'name': 'System', 'message': name + ' has entered the Room', 'datetime': int( datetime.now( timezone.utc ).timestamp() * 1000 ) } )
  emit( 
    'priorMessages', 
    existing_rooms[room]['messages'],
    to=room
  )
  existing_rooms[room]['members'].append( { 'id': request.sid, 'name': name } )
  print( f'{ name } joined Room { room }' )

@socketio.on( 'sendMessage' )
def receiveMessage( data ):
  name = ''
  room = ''
  message = ''
  
  try:
    name = data[ 'name' ]
    room = data[ 'room' ]
    message = data[ 'message' ]
  except:
    return
  
  if room not in existing_rooms:
    return
  
  if ( next((member for member in existing_rooms[room]['members'] if ((member["id"] == request.sid) and (member["name"] == name))), None) ):
    content = { 
      'name': name, 
      'message': message, 
      'datetime': int( datetime.now( timezone.utc ).timestamp() * 1000 ) 
    }

    existing_rooms[room]['messages'].append( content )
    emit( 
      'message', 
      content,
      to=room
    )
    print( f'{ name } said { message } in Room { room }' )
    
  else: 
    return

@socketio.on( 'disconnect' )
def disconnection():
  
  for room in existing_rooms:

    idx = next((idx for idx, member in enumerate(existing_rooms[room]['members']) if member["id"] == request.sid), None)

    if ( isinstance(idx, numbers.Number) ):

      leave_room( room )
      popped_member = existing_rooms[room]['members'].pop( idx )
        
      if len( existing_rooms[room]['members'] ) == 0:
        del existing_rooms[room]
        print( f'{ popped_member[ 'name' ] } left Room { room }' )
        return

      existing_rooms[room]['messages'].append( { 'name': 'System', 'message': popped_member[ 'name' ] + ' has left the Room', 'datetime': int( datetime.now( timezone.utc ).timestamp() * 1000 ) } )
      emit( 
        'message', 
        { 'name': 'System', 'message': popped_member[ 'name' ] + ' has left the Room', 'datetime': int( datetime.now( timezone.utc ).timestamp() * 1000 ) },
        to=room
      )
      print( f'{ popped_member[ 'name' ] } left Room { room }' )
      return

if __name__ == '__main__':
  socketio.run(
    app, 
    host=os.getenv('BACKEND_HOST'), 
    port=os.getenv('BACKEND_PORT'), 
    debug=True
  )
