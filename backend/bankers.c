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

// Preset configurations for fast dynamic testing
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


