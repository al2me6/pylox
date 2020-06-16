if __name__ == "__main__":
    import argparse
    from pylox.lox import Lox

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
        "--dump",
        choices=Lox.DUMP_OPTIONS,
        metavar="|".join(Lox.DUMP_OPTIONS),
        help="dump the internal state of the interpreter"
    )
    (args, extra_args) = parser.parse_known_args()

    lox = Lox(dump_option=args.dump)
    if args.source:
        lox.run_file(args.source)
    else:
        lox.run_interactive()
