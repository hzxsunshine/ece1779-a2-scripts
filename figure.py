import numpy as np
import matplotlib.pyplot as plt
import random

# Create some mock data
t = np.arange(0.0, 10.0, 0.2)
# data1 = [8,18,19,34,34,54,40,38,40,39]
# data2 = [10,5,5,2,2,2,2,2,2,2]
# data3 = [80,80,80,80,80,80,80,80,80,80]
# data4 = [20,20,20,20,20,20,20,20,20,20]


data1 = []
data2 = []

for i in range(50):
    data1.append(random.randint(1,10))
fig, ax1 = plt.subplots()

for i in range(50):
    avg = np.average(data1)
    var = np.var(data1)
    data2.append((data1[i]-avg)/(var**0.5))
color = 'tab:red'
# ax1.set_xlabel('time (minutes)')
# ax1.set_ylabel('Utilization (percentages)', color=color)
ax1.plot(t, data1, color=color)
ax1.tick_params(axis='y', labelcolor=color)
plt.ylim((-2,10))

ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

# ax1.plot(t, data3,'--',color='y',label='Growing Threshold')
# ax1.plot(t, data4,'--',color='g',label='Shrinking Threshold')

color = 'tab:blue'
ax1.plot(t, data2, color=color)
ax1.tick_params(axis='y', labelcolor=color)
# ax2.set_ylabel('Number of Instances', color=color)  # we already handled the x-label with ax1
# ax2.plot(t, data2, color=color)
# ax2.tick_params(axis='y', labelcolor=color)
# plt.ylim(0,10)

# ax1.legend(loc='upper left')
fig.tight_layout()  # otherwise the right y-label is slightly clipped
plt.savefig('case4')
plt.show()