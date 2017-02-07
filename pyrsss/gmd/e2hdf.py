import sys
import logging
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

import numpy as NP
import pandas as PD

from ..gmd.calc_e import apply_transfer_function as tf_1D
from ..gmd.calc_e_3d import apply_transfer_function as tf_3D
from ..mag.iaga2hdf import read_hdf, write_hdf
from ..usarray_emtf.index import get_index, Index
from usgs_regions import get_region


logger = logging.getLogger('pyrsss.gmd.e2hdf')


def find_1D(header):
    """
    """
    lat = header['geodetic_latitude']
    lon = header['geodetic_longitude']
    region = get_region(lat, lon)
    if region:
        region = region.replace('-', '_')
    return region


def find_3D(index,
            header,
            max_distance,
            quality=5):
    """
    ???

    max_distance is in km
    """
    lat = header['geodetic_latitude']
    lon = header['geodetic_longitude']
    return index.quality_subset(min_quality=quality).by_distance(lat, lon, max_distance)


def apply_emtf(df_E,
               df_B,
               emtf_key,
               index):
    """
    """
    logger.info('applying transfer function {}'.format(emtf_key))
    interval = NP.diff(df_B.index.values[:2])[0] / NP.timedelta64(1, 's')
    Bx = df_B.Bx.values
    By = df_B.By.values
    if emtf_key.startswith('USArray'):
        xml_fname = index[emtf_key][1]
        Ex, Ey = tf_3D(Bx, By, interval, xml_fname)
    else:
        Ex, Ey = tf_1D(Bx, By, interval, emtf_key)
    df_E[emtf_key + '_Ex'] = Ex
    df_E[emtf_key + '_Ey'] = Ey
    return df_E


def e2hdf(hdf_fname,
          source_key='B',
          key='E',
          replace=False,
          include=[],
          exclude=[],
          _3D=None,
          _1D=False,
          quality=5):
    """
    """
    # setup target DataFrame
    df, header = read_hdf(hdf_fname, source_key)
    def empty_record():
        return PD.DataFrame(index=df.index)
    if replace:
        logger.info('creating new E record')
        df_e = empty_record()
    else:
        try:
            df_e, _ = read_hdf(hdf_fname, key)
            logger.info('appending to existing E record')
        except KeyError:
            logger.info('creating new E record')
            df_e = empty_record()
    # determine which EMTFs to use
    emtf_set = set(include) - set(exclude)
    if _1D:
        emtf_1D = find_1D(header)
        if emtf_1D is not None:
            emtf_set.add(emtf_1D)
    if _3D is not None:
        d_km, repository_path = _3D
        index = get_index(repository_path)
        for emtf_3D in find_3D(index, header, d_km):
            emtf_set.add(emtf_3D)
    else:
        index = None
    # apply EMTFs
    for emtf_key in sorted(emtf_set):
        df_e = apply_emtf(df_e, df, emtf_key, index)
    # output DataFrame
    write_hdf(hdf_fname, df_e, key, header)
    return hdf_fname


def float_or_str(x):
    """
    """
    try:
        return float(x)
    except:
        return x


def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = ArgumentParser('Added modeled E field records to HDF file containing processed B field data.',
                            formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('hdf_fnames',
                        type=str,
                        nargs='*',
                        metavar='hdf_fname',
                        help='HDF file record to process')
    parser.add_argument('--source-key',
                        '-s',
                        type=str,
                        default='B',
                        help='')
    parser.add_argument('--key',
                        '-k',
                        type=str,
                        default='E',
                        help='key to associate with the processed records')
    parser.add_argument('--replace',
                        '-r',
                        action='store_true',
                        help='replace modeled E field record (otherwise, append to the existing record)')
    parser.add_argument('--include',
                        '-i',
                        nargs='+',
                        type=str,
                        default=[],
                        help='EMTFs to include')
    parser.add_argument('--exclude',
                        '-e',
                        nargs='+',
                        type=str,
                        default=[],
                        help='EMTFs to exclude')
    parser.add_argument('--1D',
                        action='store_true',
                        help='include Fernberg 1-D model result for the physiographic region at the measurement location (if interior to a physiographic region)')
    parser.add_argument('--3D',
                        type=float_or_str,
                        nargs=2,
                        help='two arguments: 1) include USArray 3-D model results within the specified geodetic distance (in km) from the measurement location and 2) the path to the USArray EMTF .xml repository')
    parser.add_argument('--quality',
                        '-q',
                        choices=range(6),
                        type=int,
                        default=5,
                        help='minimum acceptable quality USArray EMTF (i.e., 0 means use all and 5 means use only highest flagged transfer functions)')
    args = parser.parse_args(argv[1:])

    for hdf_fname in args.hdf_fnames:
        e2hdf(hdf_fname,
              source_key=args.source_key,
              key=args.key,
              replace=args.replace,
              include=args.include,
              exclude=args.exclude,
              _3D=getattr(args, '3D'),
              _1D=getattr(args, '1D'),
              quality=args.quality)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    sys.exit(main())
