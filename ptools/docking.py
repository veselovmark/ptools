
"""PTools docking."""


from __future__ import print_function

import base64
import bz2
import math

import ptools


def read_translations(filename="translation.dat"):
    """Return dictionary of translations from PDB-format file indexed by translation number (atomid)."""
    rb = ptools.Rigidbody("translation.dat")
    print("Read {:d} translations from translation.dat".format(len(rb)))
    translations = [ (rb.GetAtomProperty(i).atomId, rb.getCoords(i)) for i in xrange(len(rb)) ]
    return dict(translations)


def read_rotations(filename="rotation.dat"):
    """Return dictionary of rotations from file, each rotation is a tuple (phi, theta, chi).
    
    The rotations in the dictionary are keyed by their file line number (1-based)."""
    twopi = 2.0 * 3.14159265
    nrot_per_trans = 0
    theta = []
    nphi = []
    # read theta, phi, rot data
    # nchi is number of steps to rotate about the axis joining the ligand/receptor centers
    rotdat = open('rotation.dat', 'r')
    line = rotdat.readline().split()
    ntheta = int(line[0])
    nchi = int(line[1])
    print("ntheta, nchi: {:d} {:d}".format(ntheta, nchi))
    for i in range(ntheta):
        line = rotdat.readline().split()
        theta.append(float(line[0]))
        nphi.append(int(line[1]))
        nrot_per_trans += nphi[i] * nchi
        theta[i] = twopi * theta[i] / 360.0
        print(theta[i], nphi[i])
    rotdat.close()
    rotations = []

    print("Read {:d} rotation lines from rotation.dat".format(ntheta))
    print("{:d} rotations per translation".format(nrot_per_trans))

    rotnb = 0
    for kkk in range(ntheta):
        ssii = theta[kkk]
        phii = twopi / nphi[kkk]
        for jjj in range(nphi[kkk]):
            phiii = (jjj + 1) * phii
            for iii in range(nchi):
                rotnb += 1
                chi = (iii + 1) * twopi / nchi
                rotations.append( (rotnb, (phiii, ssii, chi)) )

    return dict(rotations)


def compress_file(filename):
    with open(filename, 'r') as f:
        content = f.read()
    compressed = bz2.compress(content)
    encoded = base64.b64encode(compressed)
    return "compressed {} : \"{}\"".format(filename, encoded)


def surreal(i):
    return i


def rmsdca(l1, l2):
    """Return the RMSD between the alpha-carbone atom of two RigidBody
    instances."""
    return ptools.Rmsd(l1.CA().CreateRigid(), l2.CA().CreateRigid())


def get_group(collection, ngroups, ngroup):
    """Divide collection into ngroups; return the ngroup-th group. Groups can be run in parallel."""
    # CHR added March-April 2017
    if type(collection) is dict:
        clist = [ (t, collection[t]) for t in sorted(collection.keys()) ]
    else:
        clist = [ t for t in collection ]
    ndata = len(clist)
    n = ndata / ngroups # integer floor
    istart = (ngroup - 1) * n
    istop = istart + n
    #print("ndata {:s} ngroups {:s}  ngroup {:s}  n {:s} istart {:s} istop {:s}".format(ndata, ngroups, ngroup, n, istart, istop))
    if ngroup == ngroups:
        # Any extras are added to the last group -- let the user beware!
        group = clist[istart:]
    else:
        group = clist[istart:istop]
    if type(collection) is dict:
        return dict(group)
    else:
        return group


def run_attract(lig, rec, translations, rotations, minimlist, ff_specs, options, ref=None, ftraj=None):
    """Run the attract docking procedure."""

    # Use appropriate rmsd calculation
    if ref is not None:
        refca = ref.CA()
        if len(refca) == 0:  # No C alpha atom, ligand is probably a dna
            rmsd_func = ptools.Rmsd
            print("No Calpha atom found for ligand (DNA?). RMSD will be "
                  "calculated on all grains")
        else:
            rmsd_func = rmsdca

    nbminim = len(minimlist)
    for transnb in sorted(translations.keys()):
        trans = translations[transnb]
        print("@@@@@@@ Translation nb {:d} @@@@@@@".format(transnb))
        rotnb=0
        for rotnb in sorted(rotations.keys()):
            rot = rotations[rotnb]
            print("----- Rotation nb {:d} -----".format(rotnb))
            print("Translation by:", trans)
            print("Rotation angles:", rot)
            minimcounter=0
            ligand = ptools.AttractRigidbody(lig)
            receptor = ptools.AttractRigidbody(rec)
    
            center = ligand.FindCenter()
            ligand.Translate(ptools.Coord3D()-center) #set ligand center of mass to 0,0,0
            ligand.AttractEulerRotate(surreal(rot[0]), surreal(rot[1]), surreal(rot[2]))
            ligand.Translate(trans)
            
            for minim in minimlist:
                minimcounter += 1
                cutoff = math.sqrt(minim['squarecutoff'])
                niter = minim['maxiter']
                print("{{ " + "minimization nb {:d} of {:d} ; cutoff= {:.2f} (A) ; maxiter= {:d}".format(minimcounter, nbminim, cutoff, niter))
    
                #performs single minimization on receptor and ligand, given maxiter=niter and restraint constant rstk
                forcefield = ff_specs['ff_class'](ff_specs['ff_file'], surreal(cutoff))
                receptor.setTranslation(False)
                receptor.setRotation(False)
                
                forcefield.AddLigand(receptor)
                forcefield.AddLigand(ligand)
                rstk = minim['rstk']  #restraint force
                #if rstk > 0.0:
                    #forcefield.SetRestraint(rstk)
    
                lbfgs_minimizer = ff_specs['minimizer_class'](forcefield)
                
                lbfgs_minimizer.minimize(niter)
                ntraj = lbfgs_minimizer.GetNumberIter()
                X = lbfgs_minimizer.GetMinimizedVars()  #optimized freedom variables after minimization
    
                output = ptools.AttractRigidbody(ligand)
    
                center = output.FindCenter()
                output.Translate(ptools.Coord3D()-center)
                output.AttractEulerRotate(surreal(X[0]), surreal(X[1]), surreal(X[2]))
                output.Translate(ptools.Coord3D(surreal(X[3]), surreal(X[4]), surreal(X[5])))
                output.Translate(center)
    
                ligand = ptools.AttractRigidbody(output)

                if ftraj is not None:
                    for iteration in range(ntraj):
                        traj = lbfgs_minimizer.GetMinimizedVarsAtIter(iteration)
                        for t in traj[0:6]:
                            ftraj.write("%f "%t)
                        ftraj.write("\n")
                    ftraj.write("~~~~~~~~~~~~~~\n")
                    
            #computes RMSD if reference structure available
            if ref is not None:
                rms = rmsd_func(ref, output)
            else:
                rms="XXXX"
    
            #calculates true energy, and rmsd if possible
            #with the new ligand position
            forcefield = ff_specs['ff_class'](ff_specs['ff_file'],  surreal(500))
            print("{:>4s} {:>6s} {:>6s} {:>13s} {:>13s} {:>13s} {:>13s}".format(' ', 'Trans', 'Rot', 'Ener', 'RmsdCA_ref', "VDW", "Coulomb"))
            pl = ptools.AttractPairList(receptor, ligand,surreal(500))
            print("{:<4s} {:6d} {:6d} {:13.7f} {:>13s} {:13.7f} {:13.7f}".format("==", transnb, rotnb, forcefield.nonbon8(receptor,ligand,pl), str(rms), forcefield.getVdw(), forcefield.getCoulomb()))
            output.PrintMatrix()