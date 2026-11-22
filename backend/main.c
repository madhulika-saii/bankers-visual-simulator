
#include <stdio.h>
#include "bankers.h"

void printAvailable(int m, int available[MAX_R]) {
    printf("Available: ");

    for (int j = 0; j < m; j++) {
        printf("%d ", available[j]);
    }

    printf("\n");
}

int main(void) {

    int n = 5;
    int m = 3;

    int allocation[MAX_P][MAX_R] = {
        {0, 1, 0},
        {2, 0, 0},
        {3, 0, 2},
        {2, 1, 1},
        {0, 0, 2}
    };

    int maximum[MAX_P][MAX_R] = {
        {7, 5, 3},
        {3, 2, 2},
        {9, 0, 2},
        {2, 2, 2},
        {4, 3, 3}
    };

    int need[MAX_P][MAX_R];
    int available[MAX_R] = {3, 3, 2};
    int safeSequence[MAX_P];

    printf("====================================\n");
    printf(" GRAPH-BASED BANKER'S ALGORITHM\n");
    printf("====================================\n");

    // Step 1: Calculate Need
    if (!calculateNeed(n, m, allocation, maximum, need)) {
        return 1;
    }

    printf("\nNEED MATRIX:\n");

    for (int i = 0; i < n; i++) {
        printf("P%d: ", i);

        for (int j = 0; j < m; j++) {
            printf("%d ", need[i][j]);
        }

        printf("\n");
    }

    // Step 2: Check initial system safety
    printAvailable(m, available);

    if (!safetyAlgorithm(
        n, m, allocation, need,
        available, safeSequence
    )) {
        printf("Initial system is unsafe. Exiting.\n");
        return 1;
    }

    // Step 3: Test a valid request from P1
    printf("\n====================================\n");
    printf("TEST: RESOURCE REQUEST BY P1\n");
    printf("====================================\n");

    int request[MAX_R] = {1, 0, 2};

    requestResources(
        1, n, m, request,
        allocation, need, available
    );

    printAvailable(m, available);

    // Step 4: Test resource release by P1
    printf("\n====================================\n");
    printf("TEST: RESOURCE RELEASE BY P1\n");
    printf("====================================\n");

    int release[MAX_R] = {1, 0, 1};

    releaseResources(
        1, m, release,
        allocation, need, available
    );

    printAvailable(m, available);

    // Step 5: Test a request exceeding Need
 // Step 5: Test an unsafe request and rollback
    printf("\n====================================\n");
    printf("TEST: UNSAFE RESOURCE REQUEST\n");
    printf("====================================\n");

    int unsafeRequest[MAX_R] = {3, 3, 0};

    requestResources(
    4, n, m, unsafeRequest,
    allocation, need, available
    );

    printAvailable(m, available);
    printf("\n====================================\n");
    printf("TEST: INVALID RESOURCE REQUEST\n");
    printf("====================================\n");

    int invalidRequest[MAX_R] = {7, 0, 0};

    requestResources(
        2, n, m, invalidRequest,
        allocation, need, available
    );

    printf("\nSimulation completed.\n");

    return 0;
}
