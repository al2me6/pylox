# `pylox`

Yet another implementation of the [Lox language](https://github.com/munificent/craftinginterpreters) by Bob Nystrom, written in type-annotated Python 3.8.

This is a work-in-progress.

The implementation here is largely based on Bob's AST-walking `jlox`, with a significant number of changes and additions.

Note that it should be considered a *translation* from Java to Python, not a *transliteration*.

This implementation attempts to preserve compatibility (or offer compatibility flags) with vanilla `jlox` as much as possible. However, due to `pylox`'s additional features, some error messages will necessarily diverge.

## Major differences compared to `jlox`

`pylox` implements a number of extensions to the Lox language and provides significant quality-of-life-improvements compared to the reference implementations.

* Better error reporting: the offending line is printed and the offending token indicated
* Uses a Pratt parser instead of `jlox`'s recursive descent parser
* Extended debug features toggled by command-line switches
* A right-associative exponentiation operator `**`
* C-style ternary if statement: `var a = foo ? 2 : 3; var b = bar ? 10 : baz ? 20 : 30;`
* Switch-case statement
* Anonymous functions

### Anonymous functions

#### Basic usage

```text
fun return_a_func() {
    var a = 3;
    return fun() { return a; };
}

fun execute_func(func) {
    func();
}

var anon_func = return_a_func();
print anon_func();
execute_func(fun() { print "Hi there!"; });
```

#### Implementation details

An `AnonymousFunctionExpr` AST node type is added.

A normal function declaration is desugared to the assignment of an anonymous function to an identifier. That is, `fun foo() {}` is equivalent to `var foo = fun() {};`.

### Switch-Case

#### Basic usage

```text
var val = 2;
switch(val) {
    "a" => print "Aaaaaaaaaaaah";
    1 => print "There is only one left.";
    2 => print "Two elephants are drinking at the pool.";
    _ => {  // This is the default case.
        print "How'd you get here?!";
        print "Get out!";
    }
}
```

#### Implementation details

This statement is implemented as an if-else-if-else chain.

If the expression being matched against has a side effect, that side effect is guaranteed to be executed exactly once.

### Grammar extension definitions

cf. [grammar of the original Lox language](https://craftinginterpreters.com/appendix-i.html).

```text
// In section "Declarations":

declaration        -> variableDeclarationStmt
                    | namedFunctionStmt
                    | statement ;

namedFunctionStmt -> "fun" IDENTIFIER functionBody ;

// In section "Statements":
statement          -> exprStmt
                    | forStmt
                    | ifStmt
                    | switchStmt
                    | printStmt
                    | returnStmt
                    | whileStmt
                    | block ;
...
switchStmt         -> "switch" "(" expression ")" "{" ( ( expression | "_" ) "=>" statement )* "}" ;
...

// In section "Expressions":
...
assignment         -> ( call "." )? IDENTIFIER "=" assignment
                    | ternary_if ;
ternary_if         -> logic_or ( "?" expression ":" logic_or )* ;
...
multiplication     -> exponentiation ( ( "/" | "*" ) exponentiation )* ;
exponentiation     -> unary ( "**" unary )* ;
...
primary            -> "true" | "false" | "nil" | "this"
                    | NUMBER | STRING | IDENTIFIER | "(" expression ")"
                    | "super" "." IDENTIFIER
                    | anonymousFunction ;
...
anonymousFunction  -> "fun" functionBody ;
functionBody       -> "("  parameters? ")" block ;
```

### To be implemented; WIP ideas

The proposals below are WIP and can change at any point.

* Module system
* `print` and `println` *functions*
  * Contingent on module system.
  * Preserve backward-compatibility by desugaring `print` "keyword" into `println` call
* Sum types and product types
  * Overlap between product types and classes?
* String interpolation: ``print `There are {var} objects`;``
  * Desugar into string concatenation
* Basic stdlib: operations on builtin types, math, time, reading from stdin, etc.
  * Under the module `std`, parts are implicitly imported.

#### Big/difficult/messy items

Note that these are entirely undeveloped.

* Represent builtin types as objects
* Builtin dynamic list, tuple types
* Indexing operator, slicing: `print arr[2:];`
  * `op$index` special method
  * `slice` index type
* Iterators
  * Enhanced for loop: `for(val : array) { print val; }`
  * `yield` keyword
  * `op$iter` special method
* Operator overloading
  * Special methods in `op$op_name` format
  * `class Foo { op$add(other) { return Foo(this.foo + other.foo); } }`
  * Desugar *all* operators (including for numbers and strings) into function calls
* Pattern matching

#### Module system

Key points:

* Files and folders are implicitly modules
* Members are private by default and can be exported with the `pub` keyword
  * Private members can be accessed by other members in the same module
* Modules are imported with the `use` keyword

##### Basic usage

Folder structure:

TODO

In `main.lox`:

```text
use std:time:clock;
use std:math:*;  // Glob imports are possible but not recommended.
use local:constants:phi;  // Locals are resolved relative to the path of the current file.
use local:constants:psi;

fun fib(n) {
    return round((phi ** n - psi ** n) / sqrt(5), 0);
}

var before = clock();
print "Calculating the 100th Fibonacci number..."
print fib(100);
print "Time taken (s):";
print (clock() - before) / 1000;
```

##### Implementation details

* Use statements are expanded by parsing and inserting used files into the AST
* Private members are marked as such during variable resolution and access is enforced statically.

#### Sum types

##### Basic usage

```text
enum Color {
    variants {
      Red,
      Green,
      Blue
    }
}

print Color:Red == Color:Green; // false

enum Meal {
    variants {
        Breakfast {  // This is a "struct" variant containing named values.
            entree,
            beverage
        },
        Dinner {
            appetizer,
            entree,
            dessert,
            beverage,
        }
    }
}

var myBreakfast = Meal:Breakfast{entree="pancake", beverage="orange juice"};
print myBreakfast.entree;  // pancake
// print myBreakfast.appetizer;  // Error: Meal:Breakfast does not have attribute "appetizer".

enum Option {
    variants {
        Some[1],  // This is a "tuple" variant that contains one value.
        None
    }

    unwrap() {
      if (this.variant == Some) {  // Gives the current variant.
        return this.0; // Values of tuple variants are accessed by position, starting from 0.
      } else {
        // TODO: figure out exceptions.
      }
    }
}

var maybeExists = Option:Some("value");
print maybeExists.variant;  // Option:Some
print maybeExists.unwrap();  // value
```

## Credit

`pylox` is licensed under the [GNU GPL, version 3](./LICENSE).

Test suites and the Lox language are the work of [Robert Nystrom](https://github.com/munificent); they are distributed under their original licenses.
