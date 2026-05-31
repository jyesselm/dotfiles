# C++ Style Standards

Shared standard for `cpp-planner`, `cpp-coder`, and `cpp-reviewer`. Modern C++17/20. Clean, simple, safe.

## Non-Negotiables

| Rule | Limit | Rationale |
|------|-------|-----------|
| Max indent levels | 3 | Use early returns, guard clauses |
| Function length | ~30 lines | Few exceptions for complex algorithms |
| File size | 300-500 lines | Split into multiple translation units |
| Tiny functions | Avoid | Only if called 3+ times or for clarity |

## Principles

- **One responsibility per function** — single, clear purpose
- **Simple > clever** — no template metaprogramming unless necessary
- **Early returns** — handle errors first, then happy path
- **RAII everywhere** — no manual resource management
- **Const correctness** — mark everything const that can be
- **Composition over inheritance** — no getters/setters theater

## Header & Class Template

```cpp
#pragma once

#include <standard_library>          // std:: headers first

#include "project/external.hpp"      // then external deps
#include "project/internal.hpp"      // then internal

namespace project {

class Foo;  // Forward declare to minimize includes

/**
 * @brief Brief description.
 */
class MyClass {
public:
    using value_type = double;

    explicit MyClass(Config config);
    ~MyClass() = default;

    [[nodiscard]] auto process(Input input) const -> Output;

private:
    Config config_;
};

}  // namespace project
```

## Function Style

```cpp
/**
 * @brief Process signal using specified method.
 * @param signal Raw signal values.
 * @param method Processing method.
 * @return Processed signal.
 * @throws std::invalid_argument If signal is empty.
 */
[[nodiscard]] auto process_signal(
    std::span<const double> signal,
    Method method = Method::zscore
) -> std::vector<double> {
    if (signal.empty()) {
        throw std::invalid_argument("Signal cannot be empty");
    }
    // Main logic (flat, readable)
}
```

## Modern C++ Preferences

- `std::optional` over nullable pointers
- `std::variant` over inheritance for closed sets
- `std::span` for non-owning array views
- `auto` with trailing return types for complex types
- Range-based for loops
- `[[nodiscard]]` on functions returning values
- `enum class` over plain enums
- spdlog for all logging
- Interfaces for dependencies (testability)

## File Organization

```
include/
  project/
    module.hpp           # Public interface only
src/
  module.cpp             # Implementation (~300-500 lines)
  module_impl.hpp        # Private helpers if needed
tests/
  module_test.cpp        # Unit tests
```

## Tool Chain (MUST pass before finishing)

```bash
clang-format -i src/*.cpp include/**/*.hpp
clang-tidy src/*.cpp -- -I include/
cmake --build build --target all
ctest --test-dir build --output-on-failure
```

All must pass before considering work complete.
