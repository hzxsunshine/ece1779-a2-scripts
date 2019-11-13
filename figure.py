import numpy as np
import matplotlib.pyplot as plt

# Create some mock data
t = np.arange(0.0, 10.0, 1)
data1 = [3,4,3,3,3,4,4,5,4,6]
data2 = [10,5,5,2,2,1,1,1,1,1]
data3 = [80,80,80,80,80,80,80,80,80,80]
data4 = [20,20,20,20,20,20,20,20,20,20]

fig, ax1 = plt.subplots()

color = 'tab:red'
ax1.set_xlabel('time (minutes)')
ax1.set_ylabel('Utilization (percentages)', color=color)
ax1.plot(t, data1, color=color)
ax1.tick_params(axis='y', labelcolor=color)
plt.ylim((0,110))

ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis

ax1.plot(t, data3,'--',color='y',label='Growing Threshold')
ax1.plot(t, data4,'--',color='g',label='Shrinking Threshold')

color = 'tab:blue'
ax2.set_ylabel('Number of Instances', color=color)  # we already handled the x-label with ax1
ax2.plot(t, data2, color=color)
ax2.tick_params(axis='y', labelcolor=color)
plt.ylim(0,12)

ax1.legend(loc='upper left')
fig.tight_layout()  # otherwise the right y-label is slightly clipped
plt.savefig('case1')
#plt.show()