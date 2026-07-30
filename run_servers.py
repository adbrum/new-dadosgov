import os
import pwd
import subprocess
import sys
import time


def _docker_env(uid_var, gid_var):
    """Resolve o UID/GID do utilizador 'dadosgov' do host e injecta-os no
    ambiente passado ao docker compose sob os nomes indicados. Se 'dadosgov'
    não existir, mantém o ambiente actual e o compose cai para os defaults
    (UID/GID 10001). Nota: variáveis de ambiente têm precedência sobre o
    ficheiro .env na interpolação do compose."""
    env = os.environ.copy()
    try:
        entry = pwd.getpwnam("dadosgov")
        env[uid_var] = str(entry.pw_uid)
        env[gid_var] = str(entry.pw_gid)
    except KeyError:
        pass
    return env


def _backend_docker_env():
    """UDATA_UID/UDATA_GID: user do container e ownership dos volumes do backend."""
    return _docker_env("UDATA_UID", "UDATA_GID")


def _frontend_docker_env():
    """NEXTJS_UID/NEXTJS_GID: user do container (build args do Dockerfile) e
    chown dos bind mounts ./logs e ./.next/cache feito pelo init-dirs."""
    return _docker_env("NEXTJS_UID", "NEXTJS_GID")


def git_pull_submodules():
    """Executa git pull nos repositórios backend e frontend"""
    for repo in ["backend", "frontend"]:
        print(f"A atualizar {repo} (git pull)...")
        result = subprocess.run(
            ["git", "pull"],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            print(f"  ✓ {repo}: {output if output else 'já atualizado'}")
        else:
            print(f"  ⚠ {repo}: {result.stderr.strip() or 'erro ao executar git pull'}")


def install_dependencies():
    """Instala as dependências dos dois projetos antes de iniciar os servidores:
    'uv sync' no backend e 'npm install' no frontend. Devolve True se ambas
    as instalações terminarem com sucesso."""
    print("\n=== Instalando dependências ===\n")

    steps = [
        ("backend", ["uv", "sync"]),
        ("frontend", ["npm", "install"]),
    ]

    for repo, cmd in steps:
        print(f"A instalar dependências do {repo} ({' '.join(cmd)})...")
        try:
            result = subprocess.run(
                cmd,
                cwd=repo,
                stdout=sys.stdout,
                stderr=sys.stderr,
            )
        except FileNotFoundError:
            print(f"  ❌ {repo}: comando '{cmd[0]}' não encontrado no PATH.")
            return False

        if result.returncode != 0:
            print(f"  ❌ {repo}: falha ao instalar dependências.")
            return False
        print(f"  ✓ {repo}: dependências instaladas.")

    return True


def stop_normal_processes():
    """Para processos normais que possam estar rodando nas portas 7000 e 3000"""
    print("Verificando e liberando portas 7000 e 3000...")

    ports = [7000, 3000]
    freed_ports = []

    for port in ports:
        try:
            # Tenta encontrar o PID do processo usando a porta
            result = subprocess.run(
                ["lsof", "-t", f"-i:{port}"],
                capture_output=True,
                text=True,
                stderr=subprocess.DEVNULL,
            )

            if result.stdout.strip():
                pids = result.stdout.strip().split("\n")
                for pid in pids:
                    try:
                        subprocess.run(
                            ["kill", "-9", pid], check=True, stderr=subprocess.DEVNULL
                        )
                        freed_ports.append(port)
                    except:
                        pass

            # Alternativa com fuser caso lsof não funcione
            if not result.stdout.strip():
                subprocess.run(
                    ["fuser", "-k", f"{port}/tcp"],
                    capture_output=True,
                    stderr=subprocess.DEVNULL,
                )
        except FileNotFoundError:
            # Se lsof não estiver disponível, tenta com fuser
            try:
                result = subprocess.run(
                    ["fuser", "-k", f"{port}/tcp"],
                    capture_output=True,
                    stderr=subprocess.DEVNULL,
                )
                if result.returncode == 0:
                    freed_ports.append(port)
            except:
                pass
        except Exception as e:
            pass

    if freed_ports:
        print(f"✓ Portas liberadas: {', '.join(map(str, freed_ports))}")
    else:
        print("✓ Portas já estão livres")

    # Aguarda um momento para garantir que as portas foram liberadas
    time.sleep(0.5)


def run_servers_normal():
    """Inicia os servidores em modo de desenvolvimento (foreground)"""
    print("\n=== Iniciando servidores em MODO DESENVOLVIMENTO ===\n")

    print("Iniciando o servidor backend (API + Celery worker)...")
    backend_process = subprocess.Popen(
        ["uv", "run", "inv", "dev"],
        cwd="backend",
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    # Aguarda um pouco para o backend iniciar
    time.sleep(2)

    print("\nIniciando o servidor frontend em modo dev...")
    frontend_process = subprocess.Popen(
        ["npm", "run", "dev", "--", "-p", "3000"],
        cwd="frontend",
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    try:
        print("\n✓ Servidores iniciados com sucesso!")
        print("  Backend:  http://localhost:7000")
        print("  Frontend: http://localhost:3000")
        print("\nPressione Ctrl+C para parar os servidores.\n")

        # Mantém o script rodando enquanto os servidores estão ativos
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\n\nSinal de interrupção recebido (Ctrl+C). Encerrando os servidores...")
        backend_process.terminate()
        frontend_process.terminate()
        backend_process.wait()
        frontend_process.wait()
        print("Servidores encerrados com sucesso.")


def run_servers_docker():
    """Inicia os servidores via Docker Compose em modo de produção
    (backend + frontend, com rebuild de imagens)"""
    print("\n=== Iniciando servidores em MODO DOCKER (PRODUÇÃO) ===\n")

    print("A limpar containers parados, imagens dangling, volumes órfãos e cache de build antiga...")
    prune_commands = [
        (["docker", "container", "prune", "-f"], "containers parados"),
        (["docker", "image", "prune", "-f"], "imagens dangling"),
        (["docker", "volume", "prune", "-f"], "volumes anónimos órfãos"),
        # Mantém até 10 GB da cache de build mais recente (builds rápidos)
        # e apaga apenas o excedente mais antigo.
        (["docker", "builder", "prune", "-f", "--max-used-space", "10GB"], "cache de build antiga"),
    ]
    for cmd, label in prune_commands:
        result = subprocess.run(cmd, stdout=sys.stdout, stderr=sys.stderr)
        if result.returncode != 0:
            print(f"  ⚠ Falha ao limpar {label}; a continuar mesmo assim.")

    # In production mode, use only the base docker-compose.yml (no override)
    compose_flag = ["-f", "docker-compose.yml"]

    backend_env = _backend_docker_env()
    if "UDATA_UID" in backend_env:
        print(
            f"  → 'dadosgov' detectado no host: "
            f"UID={backend_env['UDATA_UID']}, GID={backend_env['UDATA_GID']}"
        )
    else:
        print("  → 'dadosgov' não existe no host; a usar defaults do Dockerfile (10001).")

    print("A iniciar o backend (app + worker + beat)...")
    print("  (com rebuild de imagens)")
    backend_result = subprocess.run(
        ["docker", "compose"] + compose_flag + ["up", "-d", "--build"],
        cwd="backend",
        env=backend_env,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    if backend_result.returncode != 0:
        print("\n❌ Falha ao iniciar o backend via Docker!")
        return

    print("\nA iniciar o frontend...")
    print("  (com rebuild de imagens)")
    frontend_result = subprocess.run(
        ["docker", "compose"] + compose_flag + ["--env-file", ".env", "up", "-d", "--build"],
        cwd="frontend",
        env=_frontend_docker_env(),
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    if frontend_result.returncode != 0:
        print("\n❌ Falha ao iniciar o frontend via Docker!")
        return

    print("\n✓ Servidores Docker iniciados com sucesso!")
    print("  Backend:  http://localhost:7000 (gunicorn)")
    print("  Frontend: http://localhost:3000")
    print("\nComandos úteis:")
    print("  docker compose -f backend/docker-compose.yml logs -f     - Logs do backend")
    print("  docker compose -f frontend/docker-compose.yml logs -f    - Logs do frontend")
    print("  docker compose -f backend/docker-compose.yml down        - Parar backend")
    print("  docker compose -f frontend/docker-compose.yml down       - Parar frontend")


def restart_docker_containers():
    """Reinicia todos os containers Docker (backend + frontend)"""
    print("\n=== Reiniciando todos os containers Docker ===\n")

    compose_flag = ["-f", "docker-compose.yml"]

    print("A reiniciar os containers do backend (app + worker + beat)...")
    backend_result = subprocess.run(
        ["docker", "compose"] + compose_flag + ["restart"],
        cwd="backend",
        env=_backend_docker_env(),
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    if backend_result.returncode != 0:
        print("\n❌ Falha ao reiniciar os containers do backend!")
        return

    print("\nA reiniciar os containers do frontend...")
    frontend_result = subprocess.run(
        ["docker", "compose"] + compose_flag + ["--env-file", ".env", "restart"],
        cwd="frontend",
        env=_frontend_docker_env(),
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    if frontend_result.returncode != 0:
        print("\n❌ Falha ao reiniciar os containers do frontend!")
        return

    print("\n✓ Todos os containers foram reiniciados com sucesso!")
    print("  Backend:  http://localhost:7000")
    print("  Frontend: http://localhost:3000")


def show_menu():
    """Mostra o menu de opções"""
    print("\n" + "=" * 50)
    print("   dados.gov.pt - Gerenciador de Servidores")
    print("=" * 50)
    print("\nEscolha o modo de execução:")
    print("\n  1. Modo de Desenvolvimento (foreground)")
    print("     - Instala dependências (uv sync + npm install) antes de iniciar")
    print("     - Servidores rodam no terminal atual")
    print("     - Frontend em modo dev (npm run dev)")
    print("\n  2. Modo Docker (produção)")
    print("     - Instala dependências (uv sync + npm install) antes de iniciar")
    print("     - Backend com gunicorn (4 workers)")
    print("     - Reconstrói as imagens (sem hot-reload, sem volumes de código)")
    print("     - Limpa containers parados, imagens dangling, volumes órfãos")
    print("       e cache de build antiga (mantém 10 GB) antes de iniciar")
    print("\n  3. Reiniciar containers")
    print("     - Faz restart de todos os containers Docker (backend + frontend)")
    print("\n  0. Sair")
    print("\n" + "=" * 50)


def main():
    """Função principal"""
    while True:
        show_menu()

        try:
            choice = input("\nDigite sua opção (0-3): ").strip()

            if choice == "0":
                print("\nSaindo...")
                sys.exit(0)

            elif choice == "1":
                git_pull_submodules()
                if not install_dependencies():
                    print("\n❌ Instalação de dependências falhou; servidores não iniciados.")
                    break
                # Liberta as portas antes de iniciar
                stop_normal_processes()
                time.sleep(1)
                run_servers_normal()
                break

            elif choice == "2":
                git_pull_submodules()
                if not install_dependencies():
                    print("\n❌ Instalação de dependências falhou; containers não criados.")
                    break
                run_servers_docker()
                break

            elif choice == "3":
                restart_docker_containers()
                break

            else:
                print("\n❌ Opção inválida! Por favor, escolha 0, 1, 2 ou 3.")
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n\nOperação cancelada pelo usuário.")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Erro: {e}")
            time.sleep(2)


if __name__ == "__main__":
    main()
