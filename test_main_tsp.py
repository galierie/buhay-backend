import pytest
import warnings
import json

from typing import List

from fastapi import status
from httpx import ASGITransport, AsyncClient
from main import app, startup_event
from models import Point, TSPinput

from random import randint
import time


from tests.naive_tsp import naive_tsp # For testing
from models import TSPinput
from tests.naive_tsp.structs import Graph, Path, Coordinates
from tests.naive_tsp.utils import naive_create_graph, min_hamiltonian_paths, path_to_json_parser

from osmnx.distance import great_circle
from pprint import pprint
def total_haversine(points, n):
    total = 0
    for i in range(n):
        total += great_circle(points[i]["coordinates"][0], points[i]["coordinates"][1],points[i+1]["coordinates"][0], points[i+1]["coordinates"][1])
    return total

def generate_points(n: int) -> TSPinput:
    start: Point = {"coordinates": [randint(0, 100_000), randint(0, 100_000)]}
    other_points: List[Point] = list()
    for i in range(n-1):
        lat = float(randint(0, 100_000))
        lng = float(randint(0, 100_000))
        p = {"coordinates":[lat,lng]}
        other_points.append(p)
    ret: TSPinput = {
        "start": start,
        "other_points": other_points
    }
    return ret
  
@pytest.mark.asyncio
async def test_tsp():
    start = time()
    async with startup_event(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            request = client.build_request(url="/tsp", method="GET", 
                json={
                    "start": {"coordinates": [1,1]},
                    "other_points": [
                        {"coordinates": [10, 10]},
                        {"coordinates": [2, 2]},
                        {"coordinates": [0, 0]}
                    ]
                }
            )
            response = await client.send(request)

        end = time.time()
        # print("TIME TAKEN: ", end-start)
        print(response.json(), total_haversine(response.json(), 4))
        print(total_haversine([
            {"coordinates": [1.0, 1.0]},
            {"coordinates": [0.0, 0.0]},
            {"coordinates": [2.0, 2.0]},
            {"coordinates": [10.0,10.0]},
            {"coordinates": [1.0, 1.0]},
        ], 4))
        assert response.json() == [
            {"coordinates": [1.0, 1.0]},
            {"coordinates": [0.0, 0.0]},
            {"coordinates": [10.0, 10.0]},
            {"coordinates": [2.0, 2.0]},
            {"coordinates": [1.0, 1.0]},
        ]

@pytest.mark.asyncio
async def test_time():
    test_cases = 6
    n = 6
    total_start = time()
    for i in range(test_cases):
        body = generate_points(n)
        # print(body)
        # start = time()
        async with startup_event(app):
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                request = client.build_request(url="/tsp", method="GET", json=body)
                response = await client.send(request)
            # end = time()
            # print(response.json())
            # print(f"RANDOM TEST {i+1} TIME TAKEN: ", end-start)

    total_end = time.time()
    print(body)
    print(response.json())
    print()
    # print(f"TIME TAKEN FOR n={n} {test_cases} TEST CASES: ", total_end-total_start)
    # print(f"AVERAGE TIME FOR n={n} {test_cases} TEST CASES: ", (total_end-total_start)/test_cases)


@pytest.mark.asyncio
async def test_correctness():
    test_cases = 10 # The brute force solver might be very, very slow
    n = 6

    print(f'Testing Correctness...')

    # total_start = time.time()
    for i in range(test_cases):
        body = generate_points(n)

        G: Graph = naive_create_graph([body["start"]] + body["other_points"])
        tsp_route: Path = min_hamiltonian_paths(G)[0]
        naive_response = path_to_json_parser(tsp_route)
        pprint(body)

        async with startup_event(app):
            # tsp_start = time.time()
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as tsp_client:
                tsp_request = tsp_client.build_request(url="/tsp", method="GET", json=body)
                tsp_response = await tsp_client.send(tsp_request)
            # tsp_end = time.time()
            # print(f'Test {i + 1}, /tsp: {tsp_end - tsp_start}')

            print(f"{i}TSP: ")
            pprint(tsp_response.json())
            pprint(total_haversine(tsp_response.json(), n))
            pprint(f"{i}NVE: ") 
            pprint(naive_response) 
            pprint(total_haversine(naive_response, n))
            print()

        assert(tsp_response.json() == naive_response or tsp_response.json() == naive_response[::-1])

    # total_end = time.time()

    # print(f'Total time: {total_end - total_start}')
    # print(f'Average time per test case: {(total_end - total_start) / test_cases}')
