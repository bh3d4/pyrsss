import logging

import numpy as NP
from pyglow.pyglow import Point

from ..gpstk import PyPosition
from ..util.los_integrator import SlantIntegrator

logger = logging.getLogger('pyrsss.iri.iri_stec')


def iri_stec(dt, stn_pos, sat_pos, alt1=100, alt2=2000, epsabs=1e-1, epsrel=1e-1):
    def fun(pos):
        llh = pos.llh
        point = Point(dt, llh[0], llh[1], llh[2] / 1e3)
        point.run_iri()
        if point.ne < 0:
            logger.warning('negative IRI Ne detected (h={:.1f} [km])'.format(llh[2] / 1e3))
            return 0
        else:
            return point.ne / 1e7
    integrator = SlantIntegrator(fun, stn_pos, height1=alt1, height2=alt2)
    return integrator(sat_pos, epsabs=epsabs, epsrel=epsrel)



if __name__ == '__main__':
    from datetime import datetime

    logging.basicConfig(level=logging.INFO)

    dt = datetime(2010, 1, 1)
    stn_xyz = NP.array([4696.986004,    723.992717,   4239.681595]) * 1e3
    sat_xyz = NP.array([10741.320824,  12456.414622,  21019.082339]) * 1e3

    stec = iri_stec(dt,
                    PyPosition(*stn_xyz),
                    PyPosition(*sat_xyz))
    print(stec)
