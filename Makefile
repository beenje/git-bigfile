all: sdist

sdist:
	python setup.py sdist

clean:
	rm -rf git_bigfile.egg-info
	rm -rf dist
	rm -f gitbigfile/*.pyc
