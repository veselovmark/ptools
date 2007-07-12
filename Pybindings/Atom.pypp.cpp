// This file has been generated by Py++.

#include "Atom.pypp.hpp"
#include "boost/python.hpp"
#include "/ibpc/rhea/saladin/Src/ptools/trunk/ptools.h"

namespace bp = boost::python;

void register_Atom_class(){

    bp::class_< PTools::Atom >( "Atom", bp::init< PTools::Atomproperty, PTools::Coord3D >(( bp::arg("ap"), bp::arg("co") )) )    
        .def( 
            "GetCoords"
            , &::PTools::Atom::GetCoords )    
        .def( 
            "SetCoords"
            , &::PTools::Atom::SetCoords
            , ( bp::arg("coords") ) )    
        .def( 
            "ToPdbString"
            , &::PTools::Atom::ToPdbString )    
        .def( 
            "ToString"
            , &::PTools::Atom::ToString )    
        .def( 
            "Translate"
            , &::PTools::Atom::Translate
            , ( bp::arg("tr") ) );

}