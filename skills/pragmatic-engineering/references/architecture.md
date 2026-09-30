# Architecture patterns

Companion to [Pragmatic Engineering](../SKILL.md). Read only the sections that
fit the current task. The examples describe small, hypothetical contracts;
they are not a library to install or an architecture to impose.

## 1. Parse once at the boundary

**Use when:** data crosses a trust boundary, such as configuration, persisted
data, a request, or an external response.

**Approach:** validate the shape and domain constraints the operation needs.
Return an internal value with those guarantees. Reuse an existing validation
library for complex schemas rather than maintaining competing systems.

This example contract requires an object with an integer retry limit from
zero through five. Additional fields are ignored; a stricter contract may
reject them instead.

```ts
type RetryOptions = Readonly<{ retryLimit: number }>;

function parseRetryOptions(input: unknown): RetryOptions {
  if (
    typeof input !== "object" ||
    input === null ||
    Array.isArray(input) ||
    !("retryLimit" in input)
  ) {
    throw new TypeError("Expected retry options");
  }

  const retryLimit = input.retryLimit;
  if (
    typeof retryLimit !== "number" ||
    !Number.isInteger(retryLimit) ||
    retryLimit < 0 ||
    retryLimit > 5
  ) {
    throw new TypeError("retryLimit must be an integer from 0 through 5");
  }

  return { retryLimit };
}
```

**Limits:** these bounds belong to this example, not every retry policy.
Choose constraints from the actual contract. A TypeScript annotation alone
does not check input, and returning a default after a failed parse hides the
failure. Apply the same runtime checks in JavaScript without requiring
TypeScript syntax.

**Skip extra machinery when:** a small existing guard already establishes
the needed contract. Do not repeatedly parse trusted internal values unless
they cross another boundary or can invalidate their guarantees.

## 2. Make finite-state handling exhaustive

**Use when:** behavior depends on a closed set of variants.

**Approach:** choose a typed lookup table for uniform data, or exhaustive
control flow for variant-specific behavior. An existing matching helper is
also reasonable. A `switch` can be exhaustive without an additional library.

```ts
type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; count: number }
  | { kind: "failed" };

function assertNever(_value: never): never {
  throw new Error("Unsupported load state");
}

function describeLoad(state: LoadState): string {
  switch (state.kind) {
    case "loading":
      return "Loading";
    case "ready":
      return `${state.count} items`;
    case "failed":
      return "Could not load";
    default:
      return assertNever(state);
  }
}
```

Adding an unhandled variant makes `assertNever(state)` fail type checking.
The runtime throw remains a useful last line of defense, not a substitute for
validating external data.

**Limits:** `Record<Key, Value>` represents a complete mapping only when the
keys form the intended finite set and the data really is complete. A lookup
with arbitrary strings can still miss. Represent partial mappings and missing
results honestly rather than hiding them with a cast.

**Skip when:** a normal condition is clearer, or the values form an open set.
In JavaScript, check runtime cases and missing lookups explicitly.

## 3. Encode a useful invariant in a type

**Use when:** plain values with different guarantees are easy to confuse at
important call sites.

**Approach:** establish the invariant at a narrow constructor, then use a
distinct type internally. Keep the assertion next to the check it relies on.

```ts
declare const positiveIntegerBrand: unique symbol;
type PositiveInteger = number & {
  readonly [positiveIntegerBrand]: true;
};

function toPositiveInteger(value: unknown): PositiveInteger {
  if (
    typeof value !== "number" ||
    !Number.isSafeInteger(value) ||
    value <= 0
  ) {
    throw new TypeError("Expected a positive safe integer");
  }
  return value as PositiveInteger;
}
```

**Limits:** a brand is erased at runtime. It does not grant authorization,
escape shell input, validate a deserialized value, or stop a caller from using
an unsafe assertion. Enforce real permissions and trust boundaries at runtime.
Do not give a type a stronger name than the constructor can justify.

**Skip when:** ordinary types and a boundary check make misuse unlikely. For
JavaScript, keep the runtime validator; do not migrate the project for a brand.

## 4. Separate a consequential plan from its application

**Use when:** users need to inspect proposed mutations, operations need an
approval boundary, or a multi-step workflow benefits from explicit changes.

**Approach:** observations produce proposed changes without writing. Apply
uses those changes after the required approval. Data records are useful for
inspection, persistence, and tests; deferred functions can work for an
in-process plan but should receive write access only when applied.

The example store supplies an atomic `compareAndSet` operation: it writes only
if the current value equals the expected value. It returns `false` for a
conflict and rejects on an operational failure.

```ts
interface TextReader {
  read(key: string): Promise<string | undefined>;
}

interface TextWriter {
  compareAndSet(
    key: string,
    expected: string | undefined,
    replacement: string,
  ): Promise<boolean>;
}

type TextChange = Readonly<{
  key: string;
  expected: string | undefined;
  replacement: string;
}>;

async function planTextChange(
  reader: TextReader,
  key: string,
  replacement: string,
): Promise<TextChange | undefined> {
  const expected = await reader.read(key);
  if (expected === replacement) return undefined;
  return { key, expected, replacement };
}

async function applyTextChange(
  writer: TextWriter,
  change: TextChange,
): Promise<void> {
  const applied = await writer.compareAndSet(
    change.key,
    change.expected,
    change.replacement,
  );
  if (!applied) {
    throw new Error("Value changed; create a new plan before applying");
  }
}
```

Passing a reader interface narrows the operations available at typed call
sites. It does not make an implementation pure, prevent hidden writes, or
enforce runtime permissions. A check that reads remote state still performs
I/O. Test that the preview path issues no mutation calls.

**Limits:** the store must really implement atomic comparison and update;
a separate read followed by a write does not provide that guarantee. If the
real API lacks this operation, choose appropriate version checks, transactions,
locking, or explicitly documented concurrency limits. Do not invent an atomic
guarantee in a wrapper.

Plans can become stale. Dependent changes may need fresh information at apply
time. Define ordering, conflict handling, and partial-failure recovery for
multi-step operations; a list of changes is not automatically transactional.

**Skip when:** a small, one-shot operation does not need a plan. A top-level
`dryRun` flag is fine when it is simpler and tests demonstrate that preview
mode does not mutate state. Do not scatter the flag through every layer.

In interactive tools, request approval where required. In unattended runs,
require the project's explicit apply policy; absence of a terminal is not
consent.

## 5. Choose state ownership before functions or classes

**Use when:** designing an API or changing how it owns dependencies.

**Approach:** make required state and capabilities visible in a small API.
Functions with explicit arguments suit independent operations. Classes and
objects suit connection lifecycles, caches, state machines, subscriptions, and
other cohesive behavior.

Prefer the form that makes invalid usage difficult while fitting the existing
code. A context argument is useful when it groups related dependencies; it
becomes a liability when it exposes unrelated services to every function.
Use the project's parameter-order and naming conventions.

**Limits:** replacing a class with functions does not by itself remove hidden
state or improve testability. Narrow interfaces help with accidental misuse,
but do not replace authorization.

**Skip when:** the current shape is understandable and the task does not
require changing it. Style consistency is not a reason for a broad rewrite.

## 6. Keep effects compatible with the runtime

**Use when:** adding imports, logging, filesystem access, process execution,
or interactive behavior.

Before adopting a helper, check:

1. Where will this code run, and which APIs exist there?
2. What dependencies and module-import side effects does the helper bring?
3. Does it preserve the project's error handling, cancellation, and lifecycle?
4. Can the same goal be achieved with an existing structured API?

Use server-side helpers on the server and browser-compatible helpers in the
browser. Consider workers and restricted runtimes separately. Do not select
a logger, command runner, or validation library solely because another project
uses it.

For child processes, separate executable selection from user-controlled
arguments, disable shell interpretation where possible, and check option
parsing, environment, working directory, cancellation, and exit status. An
argument array prevents shell interpolation, not every form of argument
injection. Use an end-of-options marker only when the invoked tool supports it.

For filesystem operations, consider resolved paths, sibling-directory
prefixes, symlinks, and concurrent filesystem changes. Choose the containment
policy and supported runtime primitives deliberately; do not present a string
check as a complete filesystem security boundary.

**Skip when:** no new effect or runtime boundary is involved. Do not add a
platform abstraction before the project actually supports multiple platforms.
