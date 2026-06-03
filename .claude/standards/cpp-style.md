# C++ Style Standards

Shared standard for `cpp-planner`, `cpp-coder`, and `cpp-reviewer`. Modern C++17/20. Clean, simple, safe.

## Non-Negotiables

| Rule | Target | Rationale |
|------|--------|-----------|
| Max nesting depth | ≤3 | early returns, guard clauses |
| Function parameters | ≤4 | more → group into a struct / `Config` |
| One responsibility | always | if you need "and" to describe it, split it |

**Length is a smell, not a hard limit.** A function should be as short as it can be while telling one coherent story; a file as small as it can be while being about one thing. If a function runs long or mixes levels of abstraction, look for a missing abstraction. Never split a cohesive unit just to hit a number: ravioli code (many tiny functions you have to chase) reads worse than one honest function.

## Principles

- **One responsibility per function** — single, clear purpose
- **RAII everywhere** — no manual resource management
- **Const correctness** — mark everything const that can be
- **Composition over inheritance** — no getters/setters theater

## Human Readability (the prime directive)

Above all, write code a human can read quickly and trust. Code is read far more often than it is written, and the reader is usually a tired collaborator, a new trainee, or you in six months with no memory of this. Optimize for that reader, not for the compiler and not for your own convenience while writing. If they would have to ask you what a piece of code does, it is not done.

- **Tell a story top-down.** A function's first lines should read as its high-level steps; push details into helpers defined below it. A reader should learn *what* a function does without reading *how*.
- **Minimize what the reader must hold in mind.** Short scopes, few variables, declared at first use rather than the top of the block. Early returns and guard clauses keep the happy path flat. Avoid action at a distance: prefer values and `const`, avoid out-parameters and shared mutable state.
- **Make names do the work.** A precise name removes the need for a comment. Use one word per concept and the same word everywhere (`reactivity`, never `react`/`r`/`val` for the same thing). Names state intent and units, never type: `timeout_ms`, `coverage_depth`, `is_paired`.
- **Surface the logic.** Give a complex sub-expression a name (an "explaining variable"), and extract a compound condition into a named predicate so the `if` reads like a sentence.
  ```cpp
  // dense: the reader has to decode the condition
  if (node.left == nullptr && node.right == nullptr && node.count == 0) { ... }
  // readable: the condition names its intent
  if (is_empty_leaf(node)) { ... }
  ```
- **Comment the why, never the what.** Justify the non-obvious: a scientific rationale (cite the paper or equation), a unit, an assumption, a gotcha. Name magic numbers with a `constexpr` and explain them.
  ```cpp
  // below this depth, reactivities are dominated by noise (see Methods)
  constexpr int min_reliable_coverage = 1000;
  if (coverage < min_reliable_coverage) return;
  ```
- **Prefer boring and explicit over clever.** No nested ternaries, no template metaprogramming for its own sake, no bit-tricks without a comment. Use range-based loops and structured bindings over index arithmetic.
  ```cpp
  for (const auto& value : values) { use(value); }   // not: for (std::size_t i = 0; ...)
  ```
- **Replace flag parameters with intent.** A bare `bool` argument forces the reader to look up what `true` means. Prefer two named functions, or an `enum class`.
- **Map code onto the science.** Analysis code should read like the method it implements: name variables after the quantities, make each step visible, and state units and the rationale for every threshold, normalization, and formula (with a reference).

**The reader test (run before finishing):** reread each function and ask, "could a new lab member follow this in one pass without asking me?" If not, the fix is almost always a clearer name, a flatter structure, an explaining variable, or a single why-comment, not more comments.

## Naming

Identifiers are **`snake_case`**, except **types**, which are **`PascalCase`** (the standard C++ convention).

| Identifier | Convention | Example |
|------------|------------|---------|
| Functions / methods | `snake_case`, verb-led | `compute_reactivity`, `parse_header` |
| Variables / parameters | `snake_case`, descriptive | `normalized_signal`, `coverage_depth` |
| Member variables | `snake_case` + trailing `_` | `config_`, `read_count_` |
| Types (class/struct/enum/alias/concept) | `PascalCase` | `SignalNormalizer`, `NormalizationMethod` |
| Enumerators | `snake_case` | `NormalizationMethod::box_plot` |
| Constants / `constexpr` | `snake_case` | `constexpr double max_reactivity = 4.0;` |
| Namespaces | `snake_case`, short | `namespace rna { ... }` |
| Files | `snake_case.hpp` / `.cpp` | `signal_normalizer.hpp` |
| Macros (avoid) | `UPPER_SNAKE_CASE` | `RNA_ASSERT` |

(Exception: STL-style member trait aliases that mirror the standard library stay `snake_case` — `value_type`, `size_type`, `iterator`.)

**Descriptive names:**
- **Words over abbreviations.** `coverage_depth`, not `cd`. If you have to think about what an abbreviation means, spell it out.
- **Name length scales with scope.** A two-line loop index can be `i`; anything longer-lived or that leaves the function gets a full name. Longer and clear beats short and cryptic.
- **Booleans read as predicates:** `is_valid`, `has_coverage`, `should_retry`.
- **No `get_`/`set_` theater.** STL-style: `size()`, not `get_size()`. Units in names when ambiguous: `timeout_ms`. No Hungarian notation.

## Documentation

Use **JavaDoc-style Doxygen blocks** — `/** ... */` with a leading `*` on every line — per the [Doxygen docblock manual](https://www.doxygen.nl/manual/docblocks.html). First line is a one-sentence brief, then a blank `*` line, then the description, then `@` tags. Align `@param` continuations under the description; refer to a parameter in prose with `@p name`.

```cpp
/**
 * Normalize a signal using the specified method.
 *
 * @param raw_signal Raw probing values; must be non-empty.
 * @param method     Normalization strategy. Defaults to z-score.
 * @return Normalized signal, same length as @p raw_signal.
 * @throws std::invalid_argument if @p raw_signal is empty.
 */
```

- **Every public class, function, and free function gets a `/** */` block** with a brief, `@param` per parameter, `@return`, and `@throws` for every exception.
- **Document the contract, not the implementation** — preconditions, units, ownership, valid ranges.
- **Inline `//` comments explain WHY, not WHAT.** Keep them truthful and current; no commented-out code.

## Banners

Open every file with a file banner, and separate major sections with a section banner.

```cpp
/**
 * @file signal_normalizer.hpp
 * @brief Normalizes raw chemical-probing signal into reactivity values.
 */

/*===========================================================================
 *  Normalization helpers
 *==========================================================================*/
```

## Template

One worked skeleton; the documented method shows the function doc style, so there is no separate function section.

```cpp
#pragma once

/**
 * @file signal_normalizer.hpp
 * @brief Normalizes raw chemical-probing signal into reactivity values.
 */

#include <span>
#include <vector>

#include "rna/normalizer_config.hpp"

namespace rna {

class ReactivityProfile;  // forward declare to minimize includes

/**
 * Normalizes raw chemical-probing signal into reactivity values.
 *
 * Holds the configuration and exposes a single entry point.
 */
class SignalNormalizer {
public:
    using value_type = double;  // STL trait alias stays snake_case

    explicit SignalNormalizer(NormalizerConfig config);

    /**
     * Returns the normalized reactivity for @p raw_signal.
     *
     * @param raw_signal Non-owning view of raw values; must be non-empty.
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

Free functions use the same `/** */` doc and trailing-return style. Bodies stay flat: guard clauses first, happy path after.

## Modern C++ Preferences

- `std::optional` over nullable pointers
- `std::variant` over inheritance for closed sets
- `std::span` for non-owning array views
- `auto` with trailing return types for complex types
- Range-based for loops; structured bindings
- `[[nodiscard]]` on functions returning values
- `enum class` over plain enums
- spdlog for all logging
- Interfaces for dependencies (testability)

## File Organization

Files are `snake_case`; one primary class/module per file, named after it.

```
include/rna/signal_normalizer.hpp   # Public interface only
src/signal_normalizer.cpp           # Implementation
src/signal_normalizer_impl.hpp      # Private helpers if needed
tests/signal_normalizer_test.cpp    # Unit tests
```

## Tool Chain (MUST pass before finishing)

```bash
clang-format -i src/*.cpp include/**/*.hpp
clang-tidy src/*.cpp -- -I include/
cmake --build build --target all
ctest --test-dir build --output-on-failure
```

All must pass before considering work complete. Enforce naming via clang-tidy's
`readability-identifier-naming` (`ClassCase: CamelCase`, `FunctionCase: lower_case`,
`VariableCase: lower_case`, `PrivateMemberSuffix: _`).
