#ifndef BANKERS_H
#define BANKERS_H

#define MAX_P 10
#define MAX_R 10

int calculateNeed(
    int n, int m,
    int allocation[MAX_P][MAX_R],
    int maximum[MAX_P][MAX_R],
    int need[MAX_P][MAX_R]
);

int safetyAlgorithm(
    int n, int m,
    int allocation[MAX_P][MAX_R],
    int need[MAX_P][MAX_R],
    int available[MAX_R],
    int safeSequence[MAX_P]
);

int requestResources(
    int process, int n, int m,
    int request[MAX_R],
    int allocation[MAX_P][MAX_R],
    int need[MAX_P][MAX_R],
    int available[MAX_R]
);

int releaseResources(
    int process, int m,
    int release[MAX_R],
    int allocation[MAX_P][MAX_R],
    int need[MAX_P][MAX_R],
    int available[MAX_R]
);

int detectRAGCycle(
    int n, int m,
    int allocation[MAX_P][MAX_R],
    int request[MAX_P][MAX_R],
    int cyclePath[MAX_P * 2 + 2],
    int *cycleLength
);

int init_preset_3x2(
    int *n, int *m,
    int total[MAX_R],
    int allocation[MAX_P][MAX_R],
    int maximum[MAX_P][MAX_R],
    int need[MAX_P][MAX_R],
    int available[MAX_R]
);

int init_preset_6x4(
    int *n, int *m,
    int total[MAX_R],
    int allocation[MAX_P][MAX_R],
    int maximum[MAX_P][MAX_R],
    int need[MAX_P][MAX_R],
    int available[MAX_R]
);

int init_preset_single_instance_deadlock(
    int *n, int *m,
    int total[MAX_R],
    int allocation[MAX_P][MAX_R],
    int maximum[MAX_P][MAX_R],
    int need[MAX_P][MAX_R],
    int available[MAX_R]
);

int init_preset_single_instance_safe(
    int *n, int *m,
    int total[MAX_R],
    int allocation[MAX_P][MAX_R],
    int maximum[MAX_P][MAX_R],
    int need[MAX_P][MAX_R],
    int available[MAX_R]
);

int init_preset_mixed_instance(
    int *n, int *m,
    int total[MAX_R],
    int allocation[MAX_P][MAX_R],
    int maximum[MAX_P][MAX_R],
    int need[MAX_P][MAX_R],
    int available[MAX_R]
);

#endif
