"""Print the example registry entries as the current minimal closed loop."""

from G1_Hybrid_Graduation_Project.registry_manager import (
    build_closure_report,
    load_registry_bundle,
)


def main() -> None:
    bundle = load_registry_bundle()
    print(build_closure_report(bundle))


if __name__ == "__main__":
    main()
