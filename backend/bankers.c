#include <stdio.h>
#include "bankers.h"

// Calculate Need = Maximum - Allocation
int calculateNeed(
    int n, int m,
    int allocation[MAX_P][MAX_R],
    int maximum[MAX_P][MAX_R],
    int need[MAX_P][MAX_R]
) {
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
            if (maximum[i][j] < allocation[i][j]) {
                printf("Invalid input: Maximum < Allocation\n");
                return 0;
            }

            need[i][j] = maximum[i][j] - allocation[i][j];
        }
    }
    return 1;
}

// Banker's Safety Algorithm
int safetyAlgorithm(
    int n, int m,
    int allocation[MAX_P][MAX_R],
    int need[MAX_P][MAX_R],
    int available[MAX_R],
    int safeSequence[MAX_P]
) {
    int work[MAX_R];
    int finish[MAX_P] = {0};

    for (int j = 0; j < m; j++) {
        work[j] = available[j];
    }

    int count = 0;

    printf("\nStarting Safety Algorithm...\n");

    while (count < n) {
        int found = 0;

        for (int i = 0; i < n; i++) {
            if (!finish[i]) {
                int possible = 1;

                for (int j = 0; j < m; j++) {
                    if (need[i][j] > work[j]) {
                        possible = 0;
                        break;
                    }
                }

                printf("\nChecking P%d: ", i);

                if (possible) {
                    printf("Can execute\n");

                    for (int j = 0; j < m; j++) {
                        work[j] += allocation[i][j];
                    }

                    finish[i] = 1;
                    safeSequence[count++] = i;
                    found = 1;

                    printf("Updated Work: ");

                    for (int j = 0; j < m; j++) {
                        printf("%d ", work[j]);
                    }
                    printf("\n");
                } else {
                    printf("Cannot execute now\n");
                }
            }
        }

        if (!found) {
            printf("\nSystem is UNSAFE!\n");
            return 0;
        }
    }

    printf("\nSystem is SAFE!\n");
    printf("Safe Sequence: ");

    for (int i = 0; i < n; i++) {
        printf("P%d", safeSequence[i]);

        if (i < n - 1)
            printf(" -> ");
    }

    printf("\n");
    return 1;
}

// Request resources with safety checking and rollback
int requestResources(
    int process, int n, int m,
    int request[MAX_R],
    int allocation[MAX_P][MAX_R],
    int need[MAX_P][MAX_R],
    int available[MAX_R]
) {
    int safeSequence[MAX_P];

    if (process < 0 || process >= n) {
        printf("Invalid process number.\n");
        return 0;
    }

    for (int j = 0; j < m; j++) {
        if (request[j] < 0 || request[j] > need[process][j]) {
            printf("Request denied: Exceeds Need or is invalid.\n");
            return 0;
        }

        if (request[j] > available[j]) {
            printf("Request denied: Resources unavailable.\n");
            return 0;
        }
    }

    // Tentatively allocate resources
    for (int j = 0; j < m; j++) {
        available[j] -= request[j];
        allocation[process][j] += request[j];
        need[process][j] -= request[j];
    }

    printf("\nChecking safety after request...\n");

    if (safetyAlgorithm(
        n, m, allocation, need,
        available, safeSequence
    )) {
        printf("\nRequest GRANTED to P%d\n", process);
        return 1;
    }

    // Roll back if the new state is unsafe
    for (int j = 0; j < m; j++) {
        available[j] += request[j];
        allocation[process][j] -= request[j];
        need[process][j] += request[j];
    }

    printf("\nRequest DENIED: Unsafe allocation. Rolled back.\n");
    return 0;
}

// Release resources back to the system
int releaseResources(
    int process, int m,
    int release[MAX_R],
    int allocation[MAX_P][MAX_R],
    int need[MAX_P][MAX_R],
    int available[MAX_R]
) {
    if (process < 0 || process >= MAX_P) {
        printf("Invalid process number.\n");
        return 0;
    }

    for (int j = 0; j < m; j++) {
        if (release[j] < 0 || release[j] > allocation[process][j]) {
            printf("Invalid release amount.\n");
            return 0;
        }
    }

    for (int j = 0; j < m; j++) {
        allocation[process][j] -= release[j];
        need[process][j] += release[j];
        available[j] += release[j];
    }

    printf("\nResources successfully released by P%d.\n", process);
    return 1;
}

// ----------------------------------------------------------------------------
// Resource Allocation Graph (RAG) Cycle Detection for Single-Instance Resources
// Vertices: Process 0..n-1, Resource n..n+m-1 (total n+m vertices)
// Directed edges:
//   Resource -> Process (Allocation): (n + j) -> i  (if allocation[i][j] > 0)
//   Process -> Resource (Request):    i -> (n + j)  (if request[i][j] > 0)
// Returns 1 if a directed cycle is detected, 0 otherwise.
// If a cycle is detected, cyclePath is filled with the vertex sequence v1..vk..v1
// and *cycleLength is set.
// ----------------------------------------------------------------------------
static int dfsFindRAGCycle(
    int u, int totalV, int n, int m,
    int allocation[MAX_P][MAX_R],
    int request[MAX_P][MAX_R],
    int color[],
    int parent[],
    int cyclePath[],
    int *cycleLength
) {
    color[u] = 1; // Gray (currently exploring this branch)

    if (u < n) {
        // u is process i -> edges to resources j where request[i][j] > 0
        int i = u;
        for (int j = 0; j < m; j++) {
            if (request[i][j] > 0) {
                int v = n + j;
                if (color[v] == 1) {
                    // Back-edge found: cycle exists!
                    int temp[MAX_P * 2 + 4];
                    int tlen = 0;
                    temp[tlen++] = v;
                    int curr = u;
                    while (curr != v && curr != -1 && tlen < (MAX_P * 2 + 2)) {
                        temp[tlen++] = curr;
                        curr = parent[curr];
                    }
                    temp[tlen++] = v;

                    // Reverse to present path from v -> ... -> u -> v
                    for (int k = 0; k < tlen; k++) {
                        cyclePath[k] = temp[tlen - 1 - k];
                    }
                    *cycleLength = tlen;
                    return 1;
                } else if (color[v] == 0) {
                    parent[v] = u;
                    if (dfsFindRAGCycle(v, totalV, n, m, allocation, request, color, parent, cyclePath, cycleLength)) {
                        return 1;
                    }
                }
            }
        }
    } else {
        // u is resource j -> edges to processes i where allocation[i][j] > 0
        int j = u - n;
        for (int i = 0; i < n; i++) {
            if (allocation[i][j] > 0) {
                int v = i;
                if (color[v] == 1) {
                    // Back-edge found: cycle exists!
                    int temp[MAX_P * 2 + 4];
                    int tlen = 0;
                    temp[tlen++] = v;
                    int curr = u;
                    while (curr != v && curr != -1 && tlen < (MAX_P * 2 + 2)) {
                        temp[tlen++] = curr;
                        curr = parent[curr];
                    }
                    temp[tlen++] = v;

                    for (int k = 0; k < tlen; k++) {
                        cyclePath[k] = temp[tlen - 1 - k];
                    }
                    *cycleLength = tlen;
                    return 1;
                } else if (color[v] == 0) {
                    parent[v] = u;
                    if (dfsFindRAGCycle(v, totalV, n, m, allocation, request, color, parent, cyclePath, cycleLength)) {
                        return 1;
                    }
                }
            }
        }
    }

    color[u] = 2; // Black (fully visited)
    return 0;
}

int detectRAGCycle(
    int n, int m,
    int allocation[MAX_P][MAX_R],
    int request[MAX_P][MAX_R],
    int cyclePath[MAX_P * 2 + 2],
    int *cycleLength
) {
    if (n <= 0 || m <= 0 || n > MAX_P || m > MAX_R) {
        *cycleLength = 0;
        return 0;
    }

    int totalV = n + m;
    int color[MAX_P + MAX_R];
    int parent[MAX_P + MAX_R];

    for (int i = 0; i < totalV; i++) {
        color[i] = 0;
        parent[i] = -1;
    }

    *cycleLength = 0;

    for (int i = 0; i < totalV; i++) {
        if (color[i] == 0) {
            parent[i] = -1;
            if (dfsFindRAGCycle(i, totalV, n, m, allocation, request, color, parent, cyclePath, cycleLength)) {
                return 1;
            }
        }
    }

    return 0;
}

// ----------------------------------------------------------------------------
// Presets
// ----------------------------------------------------------------------------
int init_preset_3x2(
    int *n, int *m,
    int total[MAX_R],
    int allocation[MAX_P][MAX_R],
    int maximum[MAX_P][MAX_R],
    int need[MAX_P][MAX_R],
    int available[MAX_R]
) {
    *n = 3;
    *m = 2;
    total[0] = 5; total[1] = 5;

    int alloc[3][2] = {
        {1, 1},
        {2, 1},
        {1, 2}
    };
    int maxm[3][2] = {
        {2, 2},
        {2, 2},
        {3, 3}
    };

    for (int i = 0; i < 3; i++) {
        for (int j = 0; j < 2; j++) {
            allocation[i][j] = alloc[i][j];
            maximum[i][j] = maxm[i][j];
            need[i][j] = maxm[i][j] - alloc[i][j];
        }
    }

    for (int j = 0; j < 2; j++) {
        int used = 0;
        for (int i = 0; i < 3; i++) used += allocation[i][j];
        available[j] = total[j] - used;
    }
    return 1;
}

int init_preset_6x4(
    int *n, int *m,
    int total[MAX_R],
    int allocation[MAX_P][MAX_R],
    int maximum[MAX_P][MAX_R],
    int need[MAX_P][MAX_R],
    int available[MAX_R]
) {
    *n = 6;
    *m = 4;
    total[0] = 12; total[1] = 9; total[2] = 10; total[3] = 8;

    int alloc[6][4] = {
        {1, 1, 0, 1},
        {2, 0, 1, 1},
        {3, 1, 2, 1},
        {1, 2, 1, 0},
        {1, 0, 1, 1},
        {1, 1, 1, 1}
    };
    int maxm[6][4] = {
        {3, 2, 1, 2},
        {4, 1, 2, 2},
        {4, 2, 3, 2},
        {2, 3, 2, 1},
        {3, 2, 2, 2},
        {2, 2, 2, 2}
    };

    for (int i = 0; i < 6; i++) {
        for (int j = 0; j < 4; j++) {
            allocation[i][j] = alloc[i][j];
            maximum[i][j] = maxm[i][j];
            need[i][j] = maxm[i][j] - alloc[i][j];
        }
    }

    for (int j = 0; j < 4; j++) {
        int used = 0;
        for (int i = 0; i < 6; i++) used += allocation[i][j];
        available[j] = total[j] - used;
    }
    return 1;
}

int init_preset_single_instance_deadlock(
    int *n, int *m,
    int total[MAX_R],
    int allocation[MAX_P][MAX_R],
    int maximum[MAX_P][MAX_R],
    int need[MAX_P][MAX_R],
    int available[MAX_R]
) {
    *n = 2;
    *m = 2;
    total[0] = 1; total[1] = 1;

    for (int i = 0; i < MAX_P; i++) {
        for (int j = 0; j < MAX_R; j++) {
            allocation[i][j] = 0;
            maximum[i][j] = 0;
            need[i][j] = 0;
        }
    }

    // P0 holds R0, requests R1
    allocation[0][0] = 1; allocation[0][1] = 0;
    maximum[0][0] = 1;    maximum[0][1] = 1;
    need[0][0] = 0;       need[0][1] = 1;

    // P1 holds R1, requests R0
    allocation[1][0] = 0; allocation[1][1] = 1;
    maximum[1][0] = 1;    maximum[1][1] = 1;
    need[1][0] = 1;       need[1][1] = 0;

    available[0] = 0;
    available[1] = 0;
    return 1;
}

int init_preset_single_instance_safe(
    int *n, int *m,
    int total[MAX_R],
    int allocation[MAX_P][MAX_R],
    int maximum[MAX_P][MAX_R],
    int need[MAX_P][MAX_R],
    int available[MAX_R]
) {
    *n = 3;
    *m = 3;
    total[0] = 1; total[1] = 1; total[2] = 1;

    for (int i = 0; i < MAX_P; i++) {
        for (int j = 0; j < MAX_R; j++) {
            allocation[i][j] = 0;
            maximum[i][j] = 0;
            need[i][j] = 0;
        }
    }

    // P0 holds R0, requests R1
    allocation[0][0] = 1; allocation[0][1] = 0; allocation[0][2] = 0;
    maximum[0][0] = 1;    maximum[0][1] = 1;    maximum[0][2] = 0;
    need[0][0] = 0;       need[0][1] = 1;       need[0][2] = 0;

    // P1 holds R1, requests R2
    allocation[1][0] = 0; allocation[1][1] = 1; allocation[1][2] = 0;
    maximum[1][0] = 0;    maximum[1][1] = 1;    maximum[1][2] = 1;
    need[1][0] = 0;       need[1][1] = 0;       need[1][2] = 1;

    // P2 holds nothing, requests R2
    allocation[2][0] = 0; allocation[2][1] = 0; allocation[2][2] = 0;
    maximum[2][0] = 0;    maximum[2][1] = 0;    maximum[2][2] = 1;
    need[2][0] = 0;       need[2][1] = 0;       need[2][2] = 1;

    available[0] = 0;
    available[1] = 0;
    available[2] = 1;
    return 1;
}
