# `pylox`

Yet another implementation of the [Lox language](https://github.com/munificent/craftinginterpreters) by Bob Nystrom, written in type-annotated Python 3.8.

This is a work-in-progress.

The implementation here is largely based on Bob's AST-walking `jlox`, with some of my own changes and additions.

Note that it should be considered a *translation* from Java to Python, not a *transliteration*.

## Major differences compared to `jlox`

`pylox` implements a number of extensions to the Lox language and provides significant quality-of-life-improvements compared to the reference implementations.

* Better error reporting: the offending line is printed and the offending token indicated
* Uses a Pratt parser instead of `jlox`'s recursive descent parser
* Extended debug features toggleable by command-line switches
* A right-associative exponentiation operator `**`
* Ternary if statement: `var a = foo ? 2 : 3; var b = bar ? 10 : baz ? 20 : 30;`
* Switch-case statement: `switch(val) { "a" => foo(); "42" => { bar(); baz(); } _ => qux(); }`
  * `_` for default case
  * Desugar into `if-elif-else` chain
  * If the expression being switched against has a side effect, that side effect will be executed exactly once.

### Grammar extension definitions

cf. [grammar of the original Lox language](https://craftinginterpreters.com/appendix-i.html).

```text
// In section "Statements":
statement      -> exprStmt
                | forStmt
                | ifStmt
                | switchStmt
                | printStmt
                | returnStmt
                | whileStmt
                | block ;
...
switchStmt     -> "switch" "(" expression ")" "{" ( expression "=>" statement )* "}" ;
...

// In section "Expressions":
...
assignment     -> ( call "." )? IDENTIFIER "=" assignment
                | ternary_if ;
ternary_if     -> logic_or ( "?" expression ":" logic_or )* ;
...
multiplication -> exponentiation ( ( "/" | "*" ) exponentiation )* ;
exponentiation -> unary ( "**" unary )* ;
...
```

### To be implemented; ideas

* Bitwise operators
* Enhanced for loop: `foreach(val : array) { print val; }`
  * Desugar into regular `for` loop
* Closures/anonymous functions: `|arg1, arg2| { stmt1; stmt2; }`
  * Args are taken by reference
* String interpolation: ``print `There are {var} objects`;``
  * Desugar into string concatenation
* Basic stdlib: operations on builtin types, math, time, reading from stdin, etc.

#### Big/difficult/messy items

Note that these are undeveloped proposals.

* `print` *function*
  * Preserve backward-compatibility by desugaring `print` "keyword" into function call
  * Add warning lint
* Represent built-in types as objects
* Operator overloading
  * Special methods in `op$op_name` format
  * `class Foo { fun op$add(other) { return Foo(this.foo + other.foo); } }`
  * Desugar *all* operators (including for numbers and strings) into function calls
* Builtin dynamic list, tuple, enum, struct types
* Indexing operator, slicing: `print arr[2:];`
  * `op$index` special method
  * `slice` index type
* Iterators
  * `yield` keyword
  * `op$iter` special method
* Modules
  * Files are implicitly modules
  * Members are private by default; export with `pub` keyword
  * Relative imports: `import mod1; import ../mod2;`
  * Import items from module: `import mod1.{ Class1, function1 }; import mod2.*;`
* Pattern matching

## Credit

`pylox` is licensed under the [GNU GPL, version 3](./LICENSE).

Test suites and the Lox language are the work of [Robert Nystrom](https://github.com/munificent); they are distributed under their original licenses.
