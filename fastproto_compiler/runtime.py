RUNTIME_HEADER = r"""#ifndef FASTPROTO_RUNTIME_HPP_INCLUDED
#define FASTPROTO_RUNTIME_HPP_INCLUDED

#include <arpa/inet.h>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <span>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace fastproto {

using magic = uint32_t;
using float32 = float;
using float64 = double;
using int8 = int8_t;
using int16 = int16_t;
using int32 = int32_t;
using int64 = int64_t;
using uint8 = uint8_t;
using uint16 = uint16_t;
using uint32 = uint32_t;
using uint64 = uint64_t;

inline int8 to_network_order(int8 value) { return value; }
inline int16 to_network_order(int16 value) {
    value = htons(value);
    return value;
}
inline int32 to_network_order(int32 value) {
    value = htonl(value);
    return value;
}
inline int64 to_network_order(int64 value) {
    value = htonll(value);
    return value;
}
inline uint8 to_network_order(uint8 value) { return value; }
inline uint16 to_network_order(uint16 value) {
    value = htons(value);
    return value;
}
inline uint32 to_network_order(uint32 value) {
    value = htonl(value);
    return value;
}
inline uint64 to_network_order(uint64 value) {
    value = htonll(value);
    return value;
}
inline float32 to_network_order(float32 value) {
    uint32 temp;
    static_assert(sizeof(float32) == sizeof(uint32),
                  "Size of float32 must be 4 bytes");
    std::memcpy(&temp, &value, sizeof(float32));
    temp = htonl(temp);
    std::memcpy(&value, &temp, sizeof(float32));
    return value;
}
inline float64 to_network_order(float64 value) {
    uint64 temp;
    static_assert(sizeof(float64) == sizeof(uint64),
                  "Size of float64 must be 8 bytes");
    std::memcpy(&temp, &value, sizeof(float64));
    temp = htonll(temp);
    std::memcpy(&value, &temp, sizeof(float64));
    return value;
}

inline int8 from_network_order(int8 value) { return value; }
inline int16 from_network_order(int16 value) {
    value = ntohs(value);
    return value;
}
inline int32 from_network_order(int32 value) {
    value = ntohl(value);
    return value;
}
inline int64 from_network_order(int64 value) {
    value = ntohll(value);
    return value;
}
inline uint8 from_network_order(uint8 value) { return value; }
inline uint16 from_network_order(uint16 value) {
    value = ntohs(value);
    return value;
}
inline uint32 from_network_order(uint32 value) {
    value = ntohl(value);
    return value;
}
inline uint64 from_network_order(uint64 value) {
    value = ntohll(value);
    return value;
}
inline float32 from_network_order(float32 value) {
    uint32 temp;
    static_assert(sizeof(float32) == sizeof(uint32),
                  "Size of float32 must be 4 bytes");
    std::memcpy(&temp, &value, sizeof(float32));
    temp = ntohl(temp);
    std::memcpy(&value, &temp, sizeof(float32));
    return value;
}
inline float64 from_network_order(float64 value) {
    uint64 temp;
    static_assert(sizeof(float64) == sizeof(uint64),
                  "Size of float64 must be 8 bytes");
    std::memcpy(&temp, &value, sizeof(float64));
    temp = ntohll(temp);
    std::memcpy(&value, &temp, sizeof(float64));
    return value;
}

struct string {
    uint32_t offset;
    uint64_t size;
};

template <typename T> struct array {
    uint32_t offset;
    uint64_t size;
};

template <typename T> class Factory;

template <typename T> class Parser;

#define FASTPROTO_BUILTIN_FIELD(type, name)                                    \
  private:                                                                     \
    type name##_;                                                              \
                                                                               \
  public:                                                                      \
    void set_##name(type value) { name##_ = to_network_order(value); }         \
    type get_##name() const { return from_network_order(name##_); }

#define FASTPROTO_STRING_FIELD(name)                                           \
  private:                                                                     \
    fastproto::string name##_;                                                 \
                                                                               \
  public:                                                                      \
    void set_##name(const std::byte* buffer_start,                             \
                    const std::byte* data_start, size_t data_size) {           \
        name##_.offset = (uint32_t)(data_start - buffer_start);                \
        name##_.size = data_size;                                              \
    }                                                                          \
    std::string_view get_##name(const std::byte* buffer_start) const {         \
        return std::string_view(                                               \
            reinterpret_cast<const char*>(buffer_start + name##_.offset),      \
            name##_.size);                                                     \
    }

#define FASTPROTO_ARRAY_FIELD(type, name)                                      \
  private:                                                                     \
    fastproto::array<type> name##_;                                            \
                                                                               \
  public:                                                                      \
    void set_##name(const std::byte* buffer_start,                             \
                    const std::byte* data_start, size_t data_size) {           \
        name##_.offset = (uint32_t)(data_start - buffer_start);                \
        name##_.size = data_size;                                              \
    }                                                                          \
    std::span<const type> get_##name(const std::byte* buffer_start) const {    \
        return std::span<const type>(                                          \
            (const type*)(buffer_start + name##_.offset), name##_.size);       \
    }                                                                          \
    size_t size_##name() const { return name##_.size; }

#define FASTPROTO_FIELD(message_type, name)                                    \
  private:                                                                     \
    message_type name##_;                                                      \
                                                                               \
  public:                                                                      \
    message_type* edit_##name() { return &name##_; }                           \
    const message_type& get_##name() const { return name##_; }

#define FASTPROTO_BEGIN_STRUCT_DEFINITION(ns, name, magic_number)              \
    namespace generated::ns {                                                  \
    struct [[gnu::packed]] name {                                              \
      public:                                                                  \
        const fastproto::magic magic_ = magic_number;                          \
        static constexpr fastproto::magic magic() { return magic_number; }

#define FASTPROTO_END_STRUCT_DEFINITION()                                      \
    }                                                                          \
    ;                                                                          \
    }

#define FASTPROTO_FACTORY_BUILTIN_FIELD(type, name)                            \
  public:                                                                      \
    void set_##name(type value) { instance_.set_##name(value); }               \
    type get_##name() const { return instance_.get_##name(); }                 \
                                                                               \
  private:                                                                     \
    void serialize_##name() {}

#define FASTPROTO_FACTORY_FIELD(message_type, name)                            \
  public:                                                                      \
    message_type* edit_##name() { return instance_.edit_##name(); }            \
    const message_type& get_##name() const { return instance_.get_##name(); }  \
                                                                               \
  private:                                                                     \
    void serialize_##name() {}

#define FASTPROTO_FACTORY_STRING_FIELD(name)                                   \
  private:                                                                     \
    std::string name##_data_;                                                  \
                                                                               \
  public:                                                                      \
    void set_##name(const std::string& value) { name##_data_ = value; }        \
    std::string_view get_##name() const { return name##_data_; }               \
                                                                               \
  private:                                                                     \
    void serialize_##name() {                                                  \
        std::span<const std::byte> data((const std::byte*)name##_data_.data(), \
                                        name##_data_.size());                  \
        uint32_t offset = (uint32_t)buffer_.size();                            \
        buffer_.insert(buffer_.end(), data.begin(), data.end());               \
        instance_.set_##name(buffer_.data(), buffer_.data() + offset,          \
                             data.size());                                     \
    }

#define FASTPROTO_FACTORY_ARRAY_FIELD(type, name)                              \
  private:                                                                     \
    std::vector<type> name##_data_;                                            \
                                                                               \
  public:                                                                      \
    type* add_##name() { return &(name##_data_.emplace_back()); }              \
    void clear_##name() { name##_data_.clear(); }                              \
    std::span<const type> get_##name() const { return name##_data_; }          \
                                                                               \
  private:                                                                     \
    void serialize_##name() {                                                  \
        std::span<const std::byte> data((const std::byte*)name##_data_.data(), \
                                        name##_data_.size() * sizeof(type));   \
        uint32_t offset = (uint32_t)buffer_.size();                            \
        buffer_.insert(buffer_.end(), data.begin(), data.end());               \
        instance_.set_##name(buffer_.data(), buffer_.data() + offset,          \
                             name##_data_.size());                             \
    }

#define FASTPROTO_FACTORY_BUILTIN_ARRAY_FIELD(type, name)                      \
  private:                                                                     \
    std::vector<type> name##_data_;                                            \
                                                                               \
  public:                                                                      \
    void add_##name(const type& value) {                                       \
        name##_data_.push_back(to_network_order(value));                       \
    }                                                                          \
    void clear_##name() { name##_data_.clear(); }                              \
    size_t size_##name() const { return name##_data_.size(); }                 \
    type get_##name(size_t index) const {                                      \
        return from_network_order(name##_data_[index]);                        \
    }                                                                          \
                                                                               \
  private:                                                                     \
    void serialize_##name() {                                                  \
        std::span<const std::byte> data((const std::byte*)name##_data_.data(), \
                                        name##_data_.size() * sizeof(type));   \
        uint32_t offset = (uint32_t)buffer_.size();                            \
        buffer_.insert(buffer_.end(), data.begin(), data.end());               \
        instance_.set_##name(buffer_.data(), buffer_.data() + offset,          \
                             name##_data_.size());                             \
    }

#define FASTPROTO_BEGIN_FACTORY_DEFINITION(ns, name)                           \
    template <> class Factory<generated::ns::name> {                           \
        generated::ns::name instance_;                                         \
        std::vector<std::byte> buffer_;

#define FASTPROTO_BEGIN_SIMPLE_FACTORY_DEFINITION(ns, name)                    \
    template <> class Factory<generated::ns::name> {                           \
        generated::ns::name instance_;

#define FASTPROTO_FACTORY_SERIALIZE_FIELD(field_name) serialize_##field_name();

#define FASTPROTO_FACTORY_BEGIN_SERIALIZE()                                    \
  public:                                                                      \
    std::span<const std::byte> serialize() {                                   \
        buffer_.clear();                                                       \
        buffer_.resize(sizeof(instance_));

#define FASTPROTO_FACTORY_END_SERIALIZE()                                      \
    std::memcpy(buffer_.data(), (const std::byte*)&instance_,                  \
                sizeof(instance_));                                            \
    return buffer_;                                                            \
    }

#define FASTPROTO_END_FACTORY_DEFINITION()                                     \
    }                                                                          \
    ;

#define FASTPROTO_END_SIMPLE_FACTORY_DEFINITION()                              \
  public:                                                                      \
    std::span<const std::byte> serialize() {                                   \
        return std::span<const std::byte>((const std::byte*)&instance_,        \
                                          sizeof(instance_));                  \
    }                                                                          \
    }                                                                          \
    ;

template <typename T>
inline bool validate_buffer(std::span<const std::byte> buffer) {
    if (buffer.size() < sizeof(T)) {
        return false;
    }
    const T* message = reinterpret_cast<const T*>(buffer.data());
    return message->magic_ == T::magic();
}

#define FASTPROTO_PARSER_BUILTIN_FIELD(type, name)                             \
  public:                                                                      \
    type get_##name() const { return message()->get_##name(); }

#define FASTPROTO_PARSER_FIELD(type, name)                                     \
  public:                                                                      \
    const type& get_##name() const { return message()->get_##name(); }

#define FASTPROTO_PARSER_STRING_FIELD(type, name)                              \
  public:                                                                      \
    std::string_view get_##name() const {                                      \
        return message()->get_##name(buffer_.data());                          \
    }

#define FASTPROTO_PARSER_ARRAY_FIELD(type, name)                               \
  public:                                                                      \
    std::span<const type> get_##name() const {                                 \
        return message()->get_##name(buffer_.data());                          \
    }

#define FASTPROTO_PARSER_BUILTIN_ARRAY_FIELD(type, name)                       \
  public:                                                                      \
    type get_##name(size_t idx) const {                                        \
        return from_network_order(message()->get_##name(buffer_.data())[idx]); \
    }                                                                          \
    size_t size_##name() const { return message()->size_##name(); }

#define FASTPROTO_BEGIN_PARSER_DEFINITION(ns, name)                            \
    template <> class Parser<generated::ns::name> {                            \
        std::span<const std::byte> buffer_;                                    \
                                                                               \
      public:                                                                  \
        void parse(std::span<const std::byte> input_buffer) {                  \
            if (!validate_buffer<generated::ns::name>(input_buffer)) {         \
                throw std::runtime_error("Invalid buffer");                    \
            }                                                                  \
            buffer_ = input_buffer;                                            \
        }                                                                      \
        const generated::ns::name* message() const {                           \
            return reinterpret_cast<const generated::ns::name*>(               \
                buffer_.data());                                               \
        }

#define FASTPROTO_END_PARSER_DEFINITION()                                      \
    }                                                                          \
    ;

} // namespace fastproto

#endif // FASTPROTO_RUNTIME_HPP_INCLUDED
"""
