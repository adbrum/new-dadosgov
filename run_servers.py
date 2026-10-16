import json
import os
import pwd
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request


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


# Uma tag de versão: 'v16.0.0.12' no backend, '1.4.14' no frontend. Marcos
# operacionais como 'pre-upstream-sync-2026-05-26' não são versões e ficam de
# fora das listagens.
VERSION_TAG = re.compile(r"^v?\d+(?:\.\d+)*$")

REPO_LABELS = {"backend": "Backend (udata-pt)", "frontend": "Frontend (dadosgov-fe)"}


def _git(repo, *args):
    """Corre um comando git dentro de um submódulo e devolve o resultado."""
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)


def _fetch_tags(repo):
    """Traz as tags novas do remoto. Sem rede, continua com as que já existem
    localmente — escolher uma versão antiga não devia exigir internet."""
    if _git(repo, "fetch", "--tags", "--quiet").returncode != 0:
        print(f"  ⚠ {repo}: remoto inacessível; a usar as tags locais")


def list_versions(repo):
    """Versões publicadas de um submódulo, da mais recente para a mais antiga.

    A ordenação é '-v:refname', que compara números como números e por isso
    lida com os dois esquemas em uso: 'v16.0.0.12' no backend (quatro
    segmentos, por ser um fork do udata) e '1.4.14' no frontend (SemVer)."""
    result = _git(
        repo,
        "for-each-ref",
        "--sort=-v:refname",
        "--format=%(refname:short)|%(*committerdate:short)|%(committerdate:short)",
        "refs/tags",
    )
    if result.returncode != 0:
        return []

    versions = []
    for line in result.stdout.splitlines():
        tag, _, dates = line.partition("|")
        if not VERSION_TAG.match(tag):
            continue
        # A data que interessa é a do commit, não a da criação da tag: as tags
        # do backend foram retrodatadas e coincidem, as do frontend não -- lá
        # foram criadas as duas no mesmo dia, para commits com semanas de
        # diferença. O primeiro campo é a data do commit quando a tag é
        # anotada; o segundo cobre as tags leves, onde o primeiro vem vazio.
        dereferenced, _, direct = dates.partition("|")
        versions.append((tag, dereferenced or direct))
    return versions


def _current_ref(repo):
    """O nome da branch onde o submódulo está, ou o commit se estiver detached."""
    branch = _git(repo, "symbolic-ref", "--quiet", "--short", "HEAD")
    if branch.returncode == 0:
        return branch.stdout.strip()
    return _git(repo, "rev-parse", "--short", "HEAD").stdout.strip()


def choose_version(repo, versions, pair_hint=None):
    """Pede a versão a usar para um submódulo. Enter aceita a mais recente.

    'pair_hint' é a data da versão já escolhida para o outro repositório: os
    dois têm numerações independentes, por isso a única correspondência
    honesta entre eles é a data, e marca-se a mais próxima no tempo."""
    label = REPO_LABELS.get(repo, repo)
    latest = versions[0][0]

    closest = None
    if pair_hint:
        closest = min(versions, key=lambda v: abs(_days_between(v[1], pair_hint)))[0]

    print(f"\n--- {label} ---")
    for index, (tag, date) in enumerate(versions[:15], start=1):
        marks = []
        if tag == latest:
            marks.append("mais recente")
        if closest and tag == closest:
            marks.append("mais próxima no tempo da outra escolha")
        suffix = f"   <- {', '.join(marks)}" if marks else ""
        print(f"  {index:2}. {tag:<14} {date}{suffix}")
    if len(versions) > 15:
        print(f"  ... e mais {len(versions) - 15}; pode escrever a tag directamente")

    while True:
        answer = input(f"\nVersão [Enter = {latest}]: ").strip()
        if not answer:
            return latest
        if answer.isdigit() and 1 <= int(answer) <= len(versions):
            return versions[int(answer) - 1][0]
        if any(tag == answer for tag, _ in versions):
            return answer
        print("  ❌ Opção inválida. Escreva um número da lista ou o nome da tag.")


def _days_between(date_a, date_b):
    """Distância em dias entre duas datas 'YYYY-MM-DD'."""
    from datetime import date

    first = date(*(int(part) for part in date_a.split("-")))
    second = date(*(int(part) for part in date_b.split("-")))
    return (first - second).days


def confirm_old_backend(tag, versions):
    """As migrações de MongoDB não revertem: correr um backend anterior sobre
    uma base já migrada deixa-a com alterações que esse código desconhece, e os
    erros daí resultantes não se parecem com a sua causa. Avisa e exige uma
    confirmação escrita — só quando a versão escolhida não é a mais recente."""
    if not versions or tag == versions[0][0]:
        return True

    print(f"\n  ⚠ AVISO: {tag} é anterior à mais recente ({versions[0][0]}).")
    print("    As migrações de MongoDB não revertem. Se esta base já correu uma")
    print("    versão mais recente, ficou com alterações que este código não")
    print("    conhece, e os erros daí resultantes são difíceis de diagnosticar.")
    print("    Em Docker, use um volume de dados separado se puder.")
    return input("\n    Escreva 'sim' para continuar: ").strip().lower() == "sim"


def checkout_version(repo, tag):
    """Põe o submódulo na tag pedida. Devolve a referência de onde vinha, para
    se poder voltar atrás, ou None se não foi possível mexer."""
    if _git(repo, "status", "--porcelain").stdout.strip():
        print(f"  ❌ {repo}: tem alterações por guardar; não lhe toco.")
        return None

    previous = _current_ref(repo)
    result = _git(repo, "checkout", "--detach", tag)
    if result.returncode != 0:
        print(f"  ❌ {repo}: {result.stderr.strip()}")
        return None

    print(f"  ✓ {repo}: {tag}   (vinha de {previous})")
    return previous


def restore_refs(previous):
    """Repõe cada submódulo na referência onde estava antes da escolha."""
    for repo, ref in previous.items():
        if not ref:
            continue
        result = _git(repo, "checkout", ref)
        state = "✓" if result.returncode == 0 else "⚠"
        detail = ref if result.returncode == 0 else result.stderr.strip()
        print(f"  {state} {repo}: {detail}")


def running_backend_version():
    """A versão que o backend a correr reporta em /api/1/site/, ou None se não
    estiver de pé. Vem da metadata do pacote instalado, por isso é o que está
    mesmo a servir — não o que o git diz estar em checkout."""
    try:
        with urllib.request.urlopen("http://localhost:7000/api/1/site/", timeout=3) as response:
            return json.load(response).get("version")
    except (urllib.error.URLError, ValueError, OSError, TimeoutError):
        return None


def run_specific_version():
    """Arranca o portal numa versão escolhida de cada submódulo.

    Porta única para esta escolha: as opções 1 e 2 usam sempre o que estiver
    nas branches de trabalho, e é aqui que se pede outra coisa."""
    print("\n=== Arrancar numa versão específica ===\n")
    print("A obter as versões publicadas...")

    for repo in ("backend", "frontend"):
        _fetch_tags(repo)

    backend_versions = list_versions("backend")
    frontend_versions = list_versions("frontend")

    if not backend_versions or not frontend_versions:
        missing = "backend" if not backend_versions else "frontend"
        print(f"\n❌ Não encontrei tags de versão em {missing}.")
        return

    backend_tag = choose_version("backend", backend_versions)
    if not confirm_old_backend(backend_tag, backend_versions):
        print("\nCancelado.")
        return

    backend_date = dict(backend_versions)[backend_tag]
    frontend_tag = choose_version("frontend", frontend_versions, pair_hint=backend_date)

    print("\nA mudar os submódulos...")
    previous = {}
    previous["backend"] = checkout_version("backend", backend_tag)
    if previous["backend"] is None:
        return

    previous["frontend"] = checkout_version("frontend", frontend_tag)
    if previous["frontend"] is None:
        restore_refs({"backend": previous["backend"]})
        return

    print(f"\nBackend {backend_tag} · Frontend {frontend_tag}")
    mode = input("Arrancar em (1) desenvolvimento ou (2) Docker? [1]: ").strip() or "1"

    try:
        if mode == "2":
            run_servers_docker()
        else:
            if install_dependencies():
                stop_normal_processes()
                time.sleep(1)
                run_servers_normal()
            else:
                print("\n❌ Instalação de dependências falhou; servidores não iniciados.")
    finally:
        print("\nOs submódulos ficaram em detached HEAD, nas tags escolhidas.")
        answer = input("Repor as referências anteriores? [S/n]: ").strip().lower()
        if answer in ("", "s", "sim", "y"):
            restore_refs(previous)
        else:
            back = ", ".join(f"{repo}: git checkout {ref}" for repo, ref in previous.items() if ref)
            print(f"  Para voltar mais tarde -> {back}")


def install_dependencies():
    """Instala as dependências dos dois projetos para o modo de desenvolvimento
    local: 'uv sync' no backend e 'npm install' no frontend. Devolve True se
    ambas as instalações terminarem com sucesso. (No modo Docker não é usado:
    o build das imagens já instala as dependências.)"""
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

    # 'restart' reutiliza as imagens que já existem, por isso a versão a correr
    # é a que foi construída da última vez -- que pode não ser a que o git tem
    # agora em checkout, se alguém arrancou numa versão específica pela opção 4.
    served = running_backend_version()
    if served:
        print(f"  Versão servida pelo backend: {served}")


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
    print("     - Dependências instaladas no build das imagens (npm ci / uv sync)")
    print("     - Backend com gunicorn (4 workers)")
    print("     - Reconstrói as imagens (sem hot-reload, sem volumes de código)")
    print("     - Limpa containers parados, imagens dangling, volumes órfãos")
    print("       e cache de build antiga (mantém 10 GB) antes de iniciar")
    print("\n  3. Reiniciar containers")
    print("     - Faz restart de todos os containers Docker (backend + frontend)")
    print("     - Reutiliza as imagens actuais: não aplica alterações ao")
    print("       docker-compose.yml nem ao .env (para isso, opção 2)")
    print("\n  4. Arrancar numa versão específica")
    print("     - Lista as versões publicadas de cada repositório, com datas")
    print("     - Enter aceita a mais recente; depois escolhe-se dev ou Docker")
    print("     - As opções 1 e 2 usam sempre as branches de trabalho")
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
                # Sem instalação de dependências no host: o build das imagens
                # já corre 'npm ci' (frontend) e 'uv sync --no-dev' (backend),
                # e o compose não monta volumes de código.
                run_servers_docker()
                break

            elif choice == "3":
                restart_docker_containers()
                break

            elif choice == "4":
                # Sem git_pull_submodules(): um pull não se aplica a um
                # checkout numa tag, que é onde esta opção deixa os repos.
                run_specific_version()
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
