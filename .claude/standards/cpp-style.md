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

## Naming

Identifiers are **`snake_case`**, except **types**, which are **`PascalCase`** (the standard C++ convention). The goal is names that read like prose and need no comment to explain what they hold.

| Identifier | Convention | Example |
|------------|------------|---------|
| Functions / methods | `snake_case`, verb-led | `compute_reactivity`, `parse_header`, `load_profile` |
| Local variables / parameters | `snake_case`, descriptive | `normalized_signal`, `coverage_depth` |
| Member variables | `snake_case` + trailing `_` | `config_`, `read_count_` |
| Types (class/struct/enum/type alias/concept) | `PascalCase` | `SignalNormalizer`, `NormalizationMethod` |
| Enumerators | `snake_case` | `NormalizationMethod::box_plot` |
| Constants / `constexpr` | `snake_case` | `constexpr double max_reactivity = 4.0;` |
| Namespaces | `snake_case`, short | `namespace rna { ... }` |
| Files | `snake_case.hpp` / `.cpp` | `signal_normalizer.hpp` |
| Macros (avoid; last resort) | `UPPER_SNAKE_CASE` | `RNA_ASSERT` |

(Exception: STL-style member trait aliases that mirror the standard library stay `snake_case` for interoperability — `value_type`, `size_type`, `iterator`. Everything that is not a type is `snake_case`.)

**Descriptive names — the rules that matter most:**
- **Prefer words over abbreviations.** `coverage_depth`, not `cd`. `mutation_rate`, not `mr`. If you have to think about what an abbreviation means, spell it out.
- **Name length scales with scope.** A loop index two lines long can be `i`. Anything that lives longer, crosses lines, or leaves the function gets a full, descriptive name. Longer and clear beats short and cryptic.
- **Booleans read as predicates.** `is_valid`, `has_coverage`, `should_retry`.
- **No `get_`/`set_` theater.** STL-style accessors: `size()`, not `get_size()`. Use `set_` only when it genuinely mutates state.
- **Put units in the name when ambiguous.** `timeout_ms`, `temperature_c`, `length_nt`.
- **No Hungarian notation.** The type system already records the type; don't encode it in the name.

## Documentation

Use **JavaDoc-style Doxygen blocks** — `/** ... */` with a leading `*` on every line — per
the [Doxygen docblock manual](https://www.doxygen.nl/manual/docblocks.html). The block opens
with `/**`, the first line is a one-sentence brief, then a blank `*` line, then the detailed
description, then the `@` tags. Align `@param` continuation lines under the description text.

```cpp
/**
 * Normalize a signal using the specified method.
 *
 * Box-plot normalization is sensitive to outliers, so values are clipped before
 * scaling. The result has the same length as the input.
 *
 * @param raw_signal Raw probing values; must be non-empty.
 * @param method     Normalization strategy to apply. Defaults to z-score.
 * @return Normalized signal, same length as @p raw_signal.
 * @throws std::invalid_argument if @p raw_signal is empty.
 */
```

- **Every public class, function, and free function gets a `/** */` block** covering: a one-line brief, `@param` for each parameter, `@return`, and `@throws` for every exception it can raise.
- **Document the contract, not the implementation** — preconditions, units, ownership, valid ranges, and what the caller must guarantee. The body shows *how*; the block states *what* and *what's required*.
- Refer to a parameter in prose with `@p name`.
- **Inline comments explain WHY, not WHAT** — use a plain `//` line to justify a non-obvious choice (`// clip outliers first: box-plot normalization is sensitive to them`).
- **Keep comments truthful and current.** A stale comment is worse than none. No commented-out code; that is what version control is for.

## Banners

Open every file with a **file banner**, and separate major sections with a **section banner**, so files stay scannable.

File banner (top of every header/source):
```cpp
/**
 * @file signal_normalizer.hpp
 * @brief Normalizes raw chemical-probing signal into reactivity values.
 */
```

Section banner (between major groups within a file):
```cpp
/*===========================================================================
 *  Normalization helpers
 *==========================================================================*/
```

## Header & Class Template

```cpp
#pragma once

/**
 * @file signal_normalizer.hpp
 * @brief Normalizes raw chemical-probing signal into reactivity values.
 */

#include <span>                          // std:: headers first
#include <vector>

#include "rna/normalizer_config.hpp"     // then project deps

namespace rna {

class ReactivityProfile;  // forward declare to minimize includes

/**
 * Normalizes raw chemical-probing signal into reactivity values.
 *
 * Holds the normalization configuration and exposes a single entry point.
 */
class SignalNormalizer {
public:
    using value_type = double;  // STL-style trait alias stays snake_case

    explicit SignalNormalizer(NormalizerConfig config);
    ~SignalNormalizer() = default;

    /**
     * Returns the normalized reactivity for @p raw_signal.
     *
     * @param raw_signal Non-owning view of raw probing values; must be non-empty.
     * @return Normalized values, same length as @p raw_signal.
     * @throws std::invalid_argument if @p raw_signal is empty.
     */
    [[nodiscard]] auto normalize(std::span<const value_type> raw_signal) const
        -> std::vector<value_type>;

private:
    NormalizerConfig config_;
};

}  // namespace rna
```

## Function Style

```cpp
/**
 * Normalize a signal using the specified method.
 *
 * @param raw_signal Raw probing values; must be non-empty.
 * @param method     Normalization strategy to apply. Defaults to z-score.
 * @return Normalized signal, same length as @p raw_signal.
 * @throws std::invalid_argument if @p raw_signal is empty.
 */
[[nodiscard]] auto normalize_signal(
    std::span<const double> raw_signal,
    NormalizationMethod method = NormalizationMethod::zscore
) -> std::vector<double> {
    if (raw_signal.empty()) {
        throw std::invalid_argument("raw_signal cannot be empty");
    }
    // Box-plot normalization is sensitive to outliers, so clip them first.
    // Main logic stays flat and readable.
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

Files are `snake_case`; one primary class/module per file, named after it.

```
include/
  rna/
    signal_normalizer.hpp   # Public interface only
src/
  signal_normalizer.cpp     # Implementation (~300-500 lines)
  signal_normalizer_impl.hpp # Private helpers if needed
tests/
  signal_normalizer_test.cpp # Unit tests
```

## Tool Chain (MUST pass before finishing)

```bash
clang-format -i src/*.cpp include/**/*.hpp
clang-tidy src/*.cpp -- -I include/
cmake --build build --target all
ctest --test-dir build --output-on-failure
```

All must pass before considering work complete. Configure `clang-tidy` with the
`readability-identifier-naming` checks to enforce the conventions above
(e.g. `ClassCase: CamelCase`, `FunctionCase: lower_case`, `VariableCase: lower_case`,
`PrivateMemberSuffix: _`).
