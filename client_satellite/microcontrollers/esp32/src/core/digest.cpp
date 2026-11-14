#include "digest.h"

#include <SHA256.h>

namespace nuxiva_node {

Sha256Stream::Sha256Stream() : impl_(new SHA256()) {
    impl_->reset();
}

Sha256Stream::~Sha256Stream() = default;

void Sha256Stream::update(const uint8_t* data, size_t length) {
    impl_->update(data, length);
}

Digest Sha256Stream::finish() {
    Digest out{};
    impl_->finalize(out.data(), out.size());
    return out;
}

Digest sha256(const uint8_t* data, size_t length) {
    Sha256Stream stream;
    stream.update(data, length);
    return stream.finish();
}

}
