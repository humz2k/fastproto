#include "generated.hpp"

#include <iostream>

int main() {
    {
        fastproto::Factory<fastproto::generated::my_namespace::SimpleMessage> factory;
        factory.set_simple_int_field(10);
        auto serialized = factory.serialize();

        fastproto::Parser<fastproto::generated::my_namespace::SimpleMessage> parser;
        parser.parse(serialized);
        std::cout << "Deserialized value: " << parser.get_simple_int_field() << std::endl;
    }

    {
        fastproto::Factory<fastproto::generated::my_namespace::my_sub_namespace::my_next_sub_namespace::MessageWithString> factory;
        factory.set_my_string_field("Hello, FastProto!");
        factory.set_my_int_field(42);
        auto serialized = factory.serialize();

        fastproto::Parser<fastproto::generated::my_namespace::my_sub_namespace::my_next_sub_namespace::MessageWithString> parser;
        parser.parse(serialized);
        std::cout << "Deserialized int value: " << parser.get_my_int_field() << std::endl;
        std::cout << "Deserialized string value: " << parser.get_my_string_field() << std::endl;
    }
    return 0;
}