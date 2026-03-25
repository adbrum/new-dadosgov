import shutil
import subprocess
import sys
import time


def stop_pm2_processes():
    """Para os processos pm2 caso existam"""
    print("Parando processos pm2 existentes...")
    try:
        subprocess.run(["pm2", "delete", "backend"], capture_output=True)
        subprocess.run(["pm2", "delete", "frontend"], capture_output=True)
        print("Processos pm2 parados com sucesso.")
    except FileNotFoundError:
        print("Aviso: pm2 não está instalado.")
    except Exception as e:
        print(f"Aviso ao parar pm2: {e}")


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


def run_servers_normal(mode="dev"):
    """Inicia os servidores em modo normal"""
    modo_nome = "DESENVOLVIMENTO" if mode == "dev" else "PRODUÇÃO"
    print(f"\n=== Iniciando servidores em MODO {modo_nome} ===\n")

    print("Iniciando o servidor backend (API + Celery worker)...")
    backend_process = subprocess.Popen(
        ["uv", "run", "inv", "dev"],
        cwd="backend",
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    # Aguarda um pouco para o backend iniciar
    time.sleep(2)

    if mode == "start":
        print("\n⏳ A compilar o frontend para produção (npm run build)... isto pode demorar alguns minutos.")
        build_process = subprocess.run(
            ["npm", "run", "build"],
            cwd="frontend",
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        if build_process.returncode != 0:
            print("\n❌ Falha na compilação do frontend! A cancelar o arranque.")
            backend_process.terminate()
            backend_process.wait()
            return

    print(f"\nIniciando o servidor frontend em modo {mode}...")
    frontend_process = subprocess.Popen(
        ["npm", "run", mode, "--", "-p", "3000"],
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


def ensure_pm2_installed():
    """Verifica se pm2 está instalado e instala se necessário. Retorna True se disponível."""
    if shutil.which("pm2"):
        return True

    print("pm2 não encontrado. Instalando globalmente...")
    result = subprocess.run(
        ["npm", "install", "-g", "pm2"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"❌ Falha ao instalar pm2: {result.stderr}")
        return False

    print("✓ pm2 instalado com sucesso.")
    return True


def run_servers_pm2():
    """Inicia os servidores em modo segundo plano com pm2"""
    print("\n=== Iniciando servidores em MODO SEGUNDO PLANO (PM2) ===\n")

    if not ensure_pm2_installed():
        return

    print("Iniciando o servidor backend com pm2...")
    backend_result = subprocess.run(
        [
            "pm2",
            "start",
            "uv run udata serve",
            "--name",
            "backend",
        ],
        cwd="backend",
        capture_output=True,
        text=True,
    )

    if backend_result.returncode != 0:
        print(f"❌ Erro ao iniciar backend: {backend_result.stderr}")
        return

    time.sleep(2)

    print("Iniciando o servidor frontend com pm2...")
    frontend_result = subprocess.run(
        [
            "pm2",
            "start",
            "npx",
            "--name",
            "frontend",
            "--",
            "next",
            "dev",
            "-H",
            "0.0.0.0",
            "-p",
            "3000",
        ],
        cwd="frontend",
        capture_output=True,
        text=True,
    )

    if frontend_result.returncode != 0:
        print(f"❌ Erro ao iniciar frontend: {frontend_result.stderr}")
        subprocess.run(["pm2", "delete", "backend"], capture_output=True)
        return

    print("\n✓ Servidores iniciados em segundo plano com sucesso!")
    print("\nComandos úteis do pm2:")
    print("  pm2 list          - Lista todos os processos")
    print("  pm2 logs          - Visualiza os logs em tempo real")
    print("  pm2 logs backend  - Logs apenas do backend")
    print("  pm2 logs frontend - Logs apenas do frontend")
    print("  pm2 stop all      - Para todos os processos")
    print("  pm2 restart all   - Reinicia todos os processos")
    print("  pm2 delete all    - Remove todos os processos")

    # Mostra o status dos processos
    print("\nStatus dos processos:")
    subprocess.run(["pm2", "list"])


def run_servers_docker():
    """Inicia os servidores via Docker Compose (backend + frontend)"""
    print("\n=== Iniciando servidores em MODO DOCKER ===\n")

    print("A construir e iniciar o backend (app + worker + beat + mailpit)...")
    backend_result = subprocess.run(
        ["docker", "compose", "up", "-d", "--build"],
        cwd="backend",
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    if backend_result.returncode != 0:
        print("\n❌ Falha ao iniciar o backend via Docker!")
        return

    print("\nA construir e iniciar o frontend...")
    frontend_result = subprocess.run(
        ["docker", "compose", "up", "-d", "--build"],
        cwd="frontend",
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    if frontend_result.returncode != 0:
        print("\n❌ Falha ao iniciar o frontend via Docker!")
        return

    print("\n✓ Servidores Docker iniciados com sucesso!")
    print("  Backend:  http://localhost:7000")
    print("  Frontend: http://localhost:3000")
    print("  Mailpit:  http://localhost:8025")
    print("\nComandos úteis:")
    print("  docker compose -f backend/docker-compose.yml logs -f     - Logs do backend")
    print("  docker compose -f frontend/docker-compose.yml logs -f    - Logs do frontend")
    print("  docker compose -f backend/docker-compose.yml down        - Parar backend")
    print("  docker compose -f frontend/docker-compose.yml down       - Parar frontend")


def show_menu():
    """Mostra o menu de opções"""
    print("\n" + "=" * 50)
    print("   dados.gov.pt - Gerenciador de Servidores")
    print("=" * 50)
    print("\nEscolha o modo de execução:")
    print("\n  1. Modo de Desenvolvimento (foreground)")
    print("     - Servidores rodam no terminal atual")
    print("     - Frontend em modo dev (npm run dev)")
    print("\n  2. Modo Segundo Plano (pm2)")
    print("     - Servidores rodam em background")
    print("     - Processos gerenciados pelo pm2")
    print("\n  3. Modo de Produção (foreground)")
    print("     - Servidores rodam no terminal atual")
    print("     - Frontend em modo de produção (npm run start)")
    print("\n  4. Modo Docker")
    print("     - Backend e frontend via Docker Compose")
    print("     - Inclui Celery worker, beat e Mailpit")
    print("\n  0. Sair")
    print("\n" + "=" * 50)


def main():
    """Função principal"""
    while True:
        show_menu()

        try:
            choice = input("\nDigite sua opção (0-4): ").strip()

            if choice == "0":
                print("\nSaindo...")
                sys.exit(0)

            elif choice == "1":
                # Para todos os processos antes de iniciar
                stop_pm2_processes()
                stop_normal_processes()
                time.sleep(1)
                run_servers_normal("dev")
                break

            elif choice == "2":
                # Para todos os processos antes de iniciar
                stop_pm2_processes()
                stop_normal_processes()
                time.sleep(1)
                run_servers_pm2()
                break

            elif choice == "3":
                # Para todos os processos antes de iniciar
                stop_pm2_processes()
                stop_normal_processes()
                time.sleep(1)
                run_servers_normal("start")
                break

            elif choice == "4":
                run_servers_docker()
                break

            else:
                print("\n❌ Opção inválida! Por favor, escolha 0, 1, 2, 3 ou 4.")
                time.sleep(1)

        except KeyboardInterrupt:
            print("\n\nOperação cancelada pelo usuário.")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Erro: {e}")
            time.sleep(2)


if __name__ == "__main__":
    main()
