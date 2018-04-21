/* -*-mode:c++; tab-width: 2; indent-tabs-mode: nil; c-basic-offset: 2 -*- */

#include "util.hh"

#include "protobufs/gg.pb.h"
#include "protobufs/util.hh"
#include "thunk/ggutils.hh"
#include "util/path.hh"
#include "thunk/thunk.hh"

using namespace std;
using namespace gg;
using namespace meow;
using namespace gg::thunk;

string meow::handle_put_message( const Message & message )
{
  assert( message.opcode() == Message::OpCode::Put );

  const string & data = message.payload();
  ObjectType type = data.compare( 0, thunk::MAGIC_NUMBER.length(), thunk::MAGIC_NUMBER )
                    ? ObjectType::Value
                    : ObjectType::Thunk;

  const string hash = gg::hash::compute( data, type );
  roost::atomic_create( data, gg::paths::blob_path( hash ) );

  return hash;
}

Message meow::create_put_message( const string & hash )
{
  string requested_file = roost::read_file( gg::paths::blob_path( hash ) );
  return { Message::OpCode::Put, move( requested_file ) };
}

Message meow::create_execute_message( const Thunk & thunk,
                                      const vector<pair<string, uint32_t>> & alt_objects )
{
  auto execution_request = Thunk::execution_request( thunk );

  *execution_request.mutable_alt_objects() =
    google::protobuf::Map<string, google::protobuf::uint32_t>( alt_objects.begin(), alt_objects.end() );

  string execution_payload = protoutil::to_string( execution_request );
  return { Message::OpCode::Execute, move( execution_payload ) };
}
