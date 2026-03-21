.PHONY: lint test package clean

lint:
	python3 -m py_compile codex_multi_manager.py

test: lint
	bash tests/smoke_test.sh

package: clean
	cd .. && zip -r codex-multi-manager.zip codex-multi-manager -x 'codex-multi-manager/__pycache__/*'

clean:
	rm -rf __pycache__ .pytest_cache
