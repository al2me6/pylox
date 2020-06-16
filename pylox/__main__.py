if __name__ == "__main__":
    import argparse
    from functools import reduce

    from pylox.lox import Lox
    from pylox.utilities import Debug

    parser = argparse.ArgumentParser(
        prog="pylox",
        description="Yet another implementation of the Lox interpreter in Python",
        allow_abbrev=False
    )
    parser.add_argument(
        "source",
        metavar="FILE",
        nargs="?",
        type=str,
        default=None,
        help="the .lox file to interpret, default to interactive mode"
    )
    parser.add_argument(
        "--dbg",
        choices=tuple(option.name for option in Debug),
        action="append",
        help="pylox debugging options, multiple --dbg arguments can be passed"
    )
    (args, extra_args) = parser.parse_known_args()

    lox = Lox(reduce(lambda a, b: a | Debug[b], args.dbg, Debug(0)))
    if args.source:
        lox.run_file(args.source)
    else:
        lox.run_interactive()
