.PHONY: clean
clean:
	find . -name '*.pyo' -delete
	find . -name '*.pyc' -delete
	find . -name __pycache__ -delete
	find . -name '*~' -delete
	find . -name '.coverage.*' -delete

.PHONY: test
test:
	python -m pytest -s -vv gridstatusio/ -m "not slow" -n auto  --reruns 5 --reruns-delay 3

.PHONY: test-slow
test-slow:
	python -m pytest -s -vv gridstatusio/ -m "slow" -n auto

.PHONY: installdeps-dev
installdeps-dev:
	python -m pip install ".[dev]"
	pre-commit install

.PHONY: installdeps-test
installdeps-test:
	python -m pip install ".[test]"

.PHONY: installdeps-docs
installdeps-docs:
	python -m pip install ".[docs]"

.PHONY: lint
lint:
	ruff gridstatusio/
	black gridstatusio/ --check

.PHONY: lint-fix
lint-fix:
	ruff gridstatusio/ --fix
	black gridstatusio/

.PHONY: upgradepip
upgradepip:
	python -m pip install --upgrade pip

.PHONY: upgradebuild
upgradebuild:
	python -m pip install --upgrade build

.PHONY: upgradesetuptools
upgradesetuptools:
	python -m pip install --upgrade setuptools

.PHONY: package
package: upgradepip upgradebuild upgradesetuptools
	python -m build
	$(eval PACKAGE=$(shell python -c 'import setuptools; setuptools.setup()' --version))
	tar -zxvf "dist/gridstatusio-${PACKAGE}.tar.gz"
	mv "gridstatusio-${PACKAGE}" unpacked

.PHONY: docs
docs: clean
	make -C docs/ -e "SPHINXOPTS=-j auto" clean html
