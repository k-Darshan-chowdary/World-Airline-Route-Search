#include "MeetingCity.h"
#include "RoundTrip.h"
#include <stdexcept>
#include <string>
#include <vector>
#include <iostream>
using namespace airline;

void check(bool ok, const char* message) {
    if (!ok) throw std::runtime_error(message);
}
Graph create(int count) {
    Graph g;
    for (int i = 0; i < count; ++i)
        g.addCity("City" + std::to_string(i) + ", Test", {0, 0});
    return g;
}
void checkWalk(const Graph& g, const RoundTripResult& r, CityId start, int count) {
    check(r.status == RoundTripStatus::Found, "walk must be found");
    check(!r.path.empty() && r.path.front() == start && r.path.back() == start, "closed walk");
    check(r.flights == r.path.size()-1, "flight count");
    for (std::size_t i=1; i+1<r.path.size(); ++i)
        check(r.path[i] != start, "start city must occur only at beginning and end");
    std::vector<bool> seen(g.cityCount());
    for (std::size_t i = 0; i < r.path.size(); ++i) {
        seen[r.path[i]] = true;
        if (i && !g.hasEdge(r.path[i-1],r.path[i]))
            throw std::runtime_error("walk contains nonexistent edge");
    }
    int visited = 0;
    for(bool v: seen) if(v) ++visited;
    check(visited == count, "all reachable vertices visited");
}
int main() {
    {
        Graph g = create(6);
        for(int from=0;from<3;++from) {
            g.addEdge(from,3);g.addEdge(from,4);
        }
        g.addEdge(0,5);
        auto r = findMeetingCity(g,0,1,2);
        check(r.city && *r.city==3,"tie broken by smallest city ID");
        check(r.totalFlights && *r.totalFlights==3,"meeting sum three");
        check(r.fromA==1 && r.fromB==1 && r.fromC==1,"meeting distances");
        check(r.pathFromA==std::vector<CityId>{0,3}, "traveller A path");
        check(r.pathFromB==std::vector<CityId>{1,3}, "traveller B path");
        check(r.pathFromC==std::vector<CityId>{2,3}, "traveller C path");
        check(!findMeetingCity(g,0,1,5).city,"no common reachable candidate");
        try { (void)findMeetingCity(g,0,1,10); throw std::runtime_error("bad ID not rejected");}
        catch(const std::out_of_range&) {}
        try { (void)findMeetingCity(g,"UNKNOWN","City1, Test","City2, Test"); throw std::runtime_error("bad label not rejected");}
        catch(const std::invalid_argument&) {}
    }
    {
        Graph g = create(3);
        g.addEdge(0,1); g.addEdge(1,2);g.addEdge(2,0);
        auto r = findRoundTrip(g,0);
        check(r.method==RoundTripMethod::Exact,"small exact");
        check(r.flights==3,"cycle optimum");
        checkWalk(g,r,0,3);
    }
    {
        Graph g = create(4);
        g.addEdge(0,1);g.addEdge(1,2);
        auto r = findRoundTrip(g,0);
        check(r.status==RoundTripStatus::NoTour,"dead end forbids closed walk");
        check(r.reachableCities==3,"reachable count");
    }
    {
        Graph g=create(2);
        auto r = findRoundTrip(g,0);
        check(r.status==RoundTripStatus::Found && r.flights==0 &&
              r.path==std::vector<CityId>{0},"isolated zero-leg walk");
    }
    // Exact mode supports 18 reachable cities; larger cycles still get
    // a valid (not necessarily minimum) component-based tour.
    for(int n: {14, 15, 18, 19, 50}) {
        Graph g=create(n);
        for(int i=0;i<n;++i) g.addEdge(i,(i+1)%n);
        auto r=findRoundTrip(g,0);
        check(r.method==(n<=18?RoundTripMethod::Exact:RoundTripMethod::Heuristic),
              "exact cutoff");
        check(r.flights==static_cast<std::size_t>(n),"directed cycle length");
        checkWalk(g,r,0,n);
    }
    {
        // 19 vertices: the shortest-looking neighbor is a dead end leading
        // back to A; the other branch is a large SCC that must be covered
        // first. Nearest-neighbor greedy can get stuck; SCC ordering succeeds.
        Graph g=create(19);
        g.addEdge(0,1);
        g.addEdge(1,2);
        g.addEdge(2,0);
        g.addEdge(1,3);
        for(int i=3;i<18;++i) g.addEdge(i,i+1);
        g.addEdge(18,1);
        auto r=findRoundTrip(g,0);
        check(r.method==RoundTripMethod::Heuristic,"large SCC mode");
        checkWalk(g,r,0,19);
        check(r.path[r.path.size()-2] == 2,"must finish through sink SCC");
    }
    {
        // A-centered star: all vertices reach A, yet the only way
        // to visit two leaves would revisit A before the end.
        Graph g=create(20);
        for(int i=1;i<20;++i) { g.addEdge(0,i);g.addEdge(i,0); }
        auto r=findRoundTrip(g,0);
        check(r.status==RoundTripStatus::NoTour,
              "branched SCC DAG proves no end-only tour");
    }
    {
        Graph g=create(4);
        g.addEdge(0,1);g.addEdge(0,2);g.addEdge(1,3);
        g.addEdge(2,3);g.addEdge(3,0);
        auto r=findRoundTrip(g,0);
        check(r.status==RoundTripStatus::NoTour,
              "no tour can revisit the origin before every city is covered");
    }
    std::cout<<"Q3/Q4 DSA unit tests passed\n";
}
