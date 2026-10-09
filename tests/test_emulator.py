import argparse

from .emulator import PSPEmulator


def main(argv=None):
    parser = argparse.ArgumentParser(description="PSP Emulator prototype")
    parser.add_argument("--rom", help="Caminho para uma ROM ou arquivo binário para carregar")
    parser.add_argument("--steps", type=int, default=10, help="Número de instruções a executar")
    parser.add_argument("--demo", action="store_true", help="Executa um programa de demonstração em vez de ROM")
    parser.add_argument("--gpu-demo", action="store_true", help="Executa uma demonstração da GPU do PSP")
    args = parser.parse_args(argv)

    emulator = PSPEmulator()

    if args.demo or args.gpu_demo:
        emulator.load_demo_program()
        print("Iniciando demonstração do emulador PSP...")
    elif args.rom:
        emulator.load_rom(args.rom)
        print(f"Carregando ROM: {args.rom}")
    else:
        emulator.load_demo_program()
        print("Nenhuma ROM especificada; executando demonstração padrão.")

    emulator.run(args.steps)
    print(emulator.state_summary())
    print(emulator.gpu_summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
