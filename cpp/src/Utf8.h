#pragma once

#include <cstddef>
#include <string>

namespace airline::detail {
// Number of bytes in one Unicode scalar, or zero for malformed UTF-8.
inline std::size_t utf8ScalarBytes(const std::string& text, std::size_t offset) {
    const auto lead = static_cast<unsigned char>(text[offset]);
    if (lead < 0x80) return 1;
    unsigned code = 0, minimum = 0;
    std::size_t bytes = 0;
    if (lead >= 0xc2 && lead <= 0xdf) { code = lead & 0x1f; minimum = 0x80; bytes = 2; }
    else if (lead >= 0xe0 && lead <= 0xef) { code = lead & 0x0f; minimum = 0x800; bytes = 3; }
    else if (lead >= 0xf0 && lead <= 0xf4) { code = lead & 0x07; minimum = 0x10000; bytes = 4; }
    else return 0;
    if (text.size() - offset < bytes) return 0;
    for (std::size_t i = 1; i < bytes; ++i) {
        const auto next = static_cast<unsigned char>(text[offset + i]);
        if ((next & 0xc0) != 0x80) return 0;
        code = (code << 6) | (next & 0x3f);
    }
    return code < minimum || code > 0x10ffff || (code >= 0xd800 && code <= 0xdfff) ? 0 : bytes;
}

inline bool validUtf8(const std::string& text) {
    for (std::size_t i = 0; i < text.size();) {
        const auto bytes = utf8ScalarBytes(text, i);
        if (!bytes) return false;
        i += bytes;
    }
    return true;
}
}  // namespace airline::detail
