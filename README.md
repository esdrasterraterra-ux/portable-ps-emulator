# portable-ps-emulator

Um emulador de PlayStation Portable em fase inicial, com arquitetura modular e pronto para evoluir para suporte real de BIOS, CPU MIPS, jogos e emulação de memória.

## Visão geral

Este projeto foi criado como uma base de desenvolvimento para um emulador PSP. A estrutura atual inclui:

- Núcleo de CPU MIPS simplificado
- Mapa de memória virtual
- Stub de BIOS
- Carregador de ROM em formato genérico
- CLI de execução com demonstração interativa
- Testes automatizados de núcleo

## Status atual

Este é um scaffold funcional para estudos e desenvolvimento, e não um emulador completo de PSP. O objetivo é oferecer uma base sólida para evoluir com:

- decodificação completa de instruções MIPS32
- emulação de GPU, áudio e I/O
- suporte a arquivos `.elf`, `.pbp` e `.iso`
- renderização de framebuffer
- compatibilidade com listas de jogos e BIOS

## Estrutura

- `psp_emulator/` — código principal do emulador
- `tests/` — testes unitários

## Como executar

```bash
python -m psp_emulator --demo --steps 10
```

Ou com uma ROM fictícia:

```bash
python -m psp_emulator --rom caminho/para/arquivo.bin --steps 50
```

## Requisitos

- Python 3.11+
- Sem dependências externas

## Desenvolvimento futuro

As próximas etapas incluem:

1. Implementar um conjunto mais completo de instruções MIPS32
2. Adicionar suporte ao sistema de memória PSP
3. Emular periféricos do PSP (GPU, áudio, controladores)
4. Implementar carregamento real de `.pbp`/`.elf`
5. Criar uma interface gráfica ou terminal interativa

## Licença

MIT
