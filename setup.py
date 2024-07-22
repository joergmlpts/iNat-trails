from distutils.core import setup, Extension

def long_description() -> str:
    "Return contents of README.md as long package description."
    with open('README.md', 'rt', encoding='utf-8') as f:
        return f.read()

setup(name='inattrails',
      version='0.9.9',
      package_dir={'inattrails': 'src/inattrails'},
      packages=['inattrails'],
      author='joergmlpts',
      author_email='joergmlpts@outlook.com',
      description='This tool reads the route of a hike and generates a table '
      'of iNaturalist observations along the trails. It also shows the '
      'observations and the route of the hike on a map. Moreover, it saves '
      'waypoints of the iNaturalist observations for offline navigation with '
      'a GPS device or smartphone.',
      readme="README.md",
      long_description=long_description(),
      long_description_content_type='text/markdown',
      url='https://github.com/joergmlpts/iNat-trails',
      classifier=[
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Developers',
          'Intended Audience :: End Users/Desktop',
          'License :: OSI Approved :: MIT License',
          'Operating System :: POSIX',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3 :: Only',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Programming Language :: Python :: 3.10',
          'Programming Language :: Python :: 3.11',
          'Programming Language :: Python :: 3.12',
          'Programming Language :: Python :: 3.13',
      ],
      entry_points = {
              'console_scripts': [
                  'inat-trails=inattrails.main:main',
              ],              
          },
      python_requires='>=3.7',
      install_requires=['aiohttp', 'shapely', 'folium'],
      )
