#include "generated/generated.hpp"
#include <iostream>

int main(){
    fastproto::Factory<fastproto::generated::test_namespace::test1> factory;
    factory.set_field1(42);
    auto buffer = factory.serialize();
    std::cout << "Serialized buffer size: " << buffer.size() << " bytes" << std::endl;
    fastproto::Parser<fastproto::generated::test_namespace::test1> parser;
    parser.parse(buffer);
    std::cout << "Parsed field1: " << parser.get_field1() << std::endl;

    fastproto::Factory<fastproto::generated::test_namespace::test2> factory2;
    factory2.set_field1(5);
    factory2.set_field2("Hello, World!");
    auto buffer2 = factory2.serialize();
    std::cout << "Serialized buffer2 size: " << buffer2.size() << " bytes" << std::endl;
    fastproto::Parser<fastproto::generated::test_namespace::test2> parser2;
    parser2.parse(buffer2);
    std::cout << "Parsed field1: " << parser2.get_field1() << std::endl;
    std::cout << "Parsed field2: " << parser2.get_field2() << std::endl;
    return 0;
}