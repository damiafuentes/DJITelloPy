basepath=$(cd `dirname $0`; pwd)
cd $basepath
cd ..
rm -rf build dist output robomaster_media_decoder.egg-info

/opt/python/cp36-cp36m/bin/python setup.py build
/opt/python/cp36-cp36m/bin/python setup.py bdist_wheel
/opt/python/cp36-cp36m/bin/auditwheel repair ./dist/`ls ./dist |grep cp36-cp36m`

rm -rf build dist output robomaster_media_decoder.egg-info
/opt/python/cp37-cp37m/bin/python setup.py build
/opt/python/cp37-cp37m/bin/python setup.py bdist_wheel
/opt/python/cp37-cp37m/bin/auditwheel repair ./dist/`ls ./dist |grep cp37-cp37m`

rm -rf build dist output robomaster_media_decoder.egg-info
/opt/python/cp38-cp38/bin/python setup.py build
/opt/python/cp38-cp38/bin/python setup.py bdist_wheel
/opt/python/cp38-cp38/bin/auditwheel repair ./dist/`ls ./dist |grep cp38-cp38`
