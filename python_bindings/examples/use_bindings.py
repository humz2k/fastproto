import fastproto_example_bindings as fp

simple = fp.SimpleMessageFactory()
simple.simple_int_field = 10
simple_data = simple.serialize()
simple_parsed = fp.SimpleMessageParser(simple_data)
print("simple_int_field:", simple_parsed.simple_int_field)

with_string = fp.MessageWithStringFactory()
with_string.my_int_field = 42
with_string.my_string_field = "Hello from Python"
with_string_data = with_string.serialize()
with_string_parsed = fp.MessageWithStringParser(with_string_data)
print("my_int_field:", with_string_parsed.my_int_field)
print("my_string_field:", with_string_parsed.my_string_field)

with_array = fp.MessageWithArrayFactory()
first = with_array.add_my_array_field()
first.simple_int_field = 100
second = with_array.add_my_array_field()
second.simple_int_field = 201
with_array.add_my_builtin_array_field(69420)
with_array.add_my_builtin_array_field(8164)
with_array_data = with_array.serialize()
with_array_parsed = fp.MessageWithArrayParser(with_array_data)
print(
    "my_array_field:",
    [message.simple_int_field for message in with_array_parsed.my_array_field],
)
print("my_builtin_array_field:", with_array_parsed.my_builtin_array_field)
