#include "generated.hpp"

#include <iostream>

int main() {
    {
        fastproto::Factory<fastproto::generated::my_namespace::SimpleMessage>
            factory;
        factory.set_simple_int_field(10);
        auto serialized = factory.serialize();

        fastproto::Parser<fastproto::generated::my_namespace::SimpleMessage>
            parser;
        parser.parse(serialized);
        std::cout << "Deserialized value: " << parser.get_simple_int_field()
                  << std::endl;
    }

    {
        fastproto::Factory<
            fastproto::generated::my_namespace::my_sub_namespace::
                my_next_sub_namespace::MessageWithString>
            factory;
        factory.set_my_string_field("Hello, FastProto!");
        factory.set_my_int_field(42);
        auto serialized = factory.serialize();

        fastproto::Parser<fastproto::generated::my_namespace::my_sub_namespace::
                              my_next_sub_namespace::MessageWithString>
            parser;
        parser.parse(serialized);
        std::cout << "Deserialized int value: " << parser.get_my_int_field()
                  << std::endl;
        std::cout << "Deserialized string value: "
                  << parser.get_my_string_field() << std::endl;
    }

    {
        fastproto::Factory<fastproto::generated::my_namespace::MessageWithArray>
            factory;
        {
            auto* new_element = factory.add_my_array_field();
            new_element->set_simple_int_field(100);
        }
        {
            auto* new_element = factory.add_my_array_field();
            new_element->set_simple_int_field(201);
        }

        factory.add_my_builtin_array_field(69420);
        factory.add_my_builtin_array_field(8164);

        auto serialized = factory.serialize();

        fastproto::Parser<fastproto::generated::my_namespace::MessageWithArray>
            parser;
        parser.parse(serialized);
        std::cout << "Deserialized repeated int values: ";
        for (const auto& value : parser.get_my_array_field()) {
            std::cout << value.get_simple_int_field() << " ";
        }
        std::cout << std::endl;

        std::cout << "Deserialized repeated builtin int values: ";
        for (size_t i = 0; i < parser.size_my_builtin_array_field(); ++i) {
            std::cout << parser.get_my_builtin_array_field(i) << " ";
        }
        std::cout << std::endl;
    }
    return 0;
}
