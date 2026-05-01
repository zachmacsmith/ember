# CHARME's per-step "atom_system" binary.
#
# CHARME is an RL policy: every step the agent picks a logical node, and a C++
# helper extends the current Chimera embedding to cover that node. The helper
# is a *variant* of ATOM with an incremental-state CLI and is *not*
# interchangeable with the standard `atom` binary shipped under external/atom.
#
# Install layout (after `ember install-binary charme`):
#   <user_binary_dir>/charme/
#     main            ← this binary
#     main.version    ← plain-text version sidecar
#     atom_log/       ← scratch directory the binary writes to per call
#
# Build locally:
#   make
# Install into the user binary dir without going through release assets:
#   make install
all:
	g++ -O3 utilities/src/*.cpp main.cpp -std=c++11 -o main -pthread

clean:
	rm -f main

.PHONY: all clean install
install: all
	@python3 -c "from ember_qc._paths import get_user_binary_dir; \
	             import shutil, os; \
	             d = get_user_binary_dir()/'charme'; \
	             d.mkdir(parents=True, exist_ok=True); \
	             shutil.copy2('main', d/'main'); \
	             (d/'atom_log').mkdir(exist_ok=True); \
	             print('Installed CHARME binary →', d/'main')"
