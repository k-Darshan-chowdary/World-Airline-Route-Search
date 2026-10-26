#include "RequiredStops.h"
#include "Graph.h"
#include <stdexcept>
#include <string>
#include <vector>
#include <iostream>
using namespace airline;
void require(bool value,const char* what){if(!value)throw std::runtime_error(what);}
int main() {
    Graph graph;
    for (const std::string& name : {"A, Testland","B, Testland","C, Testland","D, Testland","E, Testland"})
        graph.addCity(name,{0,0});
    // B->C and C->B are both present; order A->C->B->D wins here.
    graph.addEdge(0,1); graph.addEdge(1,4); graph.addEdge(4,2); graph.addEdge(2,3);
    graph.addEdge(0,2); graph.addEdge(2,1); graph.addEdge(1,3);
    graph.sortNeighbors();
    auto r=searchRequiredStops(graph,0,1,2,3);
    require(r.status==RequiredStopsStatus::Found,"route exists");
    require((r.path==std::vector<CityId>{0,2,1,3}),"choose shorter order");
    require((r.waypointOrder==std::vector<CityId>{2,1}),"waypoint order");
    require(r.flights==3 && r.connections==2,"counts");
    auto same=searchRequiredStops(graph,0,0,0,0);
    require(same.status==RequiredStopsStatus::Found && same.flights==0 && same.connections==0,"same city");
    Graph isolated;
    isolated.addCity("A, Testland",{0,0});isolated.addCity("B, Testland",{0,0});
    isolated.addCity("C, Testland",{0,0});isolated.addCity("D, Testland",{0,0});
    isolated.addEdge(0,1);isolated.addEdge(1,2);
    require(searchRequiredStops(isolated,0,1,2,3).status==RequiredStopsStatus::Unreachable,"unreachable");
    try{searchRequiredStops(graph,0,1,2,99); throw std::runtime_error("no invalid id exception");}
    catch(const std::out_of_range&){ }
    try{searchRequiredStops(graph,"No City","B, Testland","C, Testland","D, Testland"); throw std::runtime_error("no invalid name exception");}
    catch(const std::invalid_argument&){ }
    std::cout<<"Q2 core unit tests passed\n";
}
