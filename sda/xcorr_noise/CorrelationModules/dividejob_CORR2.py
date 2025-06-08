import os
import sys

import subprocess as sub

workdir='/home/obs-etu/Proj_GW/SCRIPTS_CCs/correlations/'
jobid=1

sublist_date=1
sublist_stations=1
index_stations=0
#LoadDirectory='/home/physquake-01/zigone/Trace_2012-NEW/'
LoadDirectory='/home/obs-etu/Proj_GW/DATA/TRACES/Traces_EXP1/'
SaveDirectory='/home/obs-etu/Proj_GW/DATA/CORR/CORR_EXP1/'
compo1=['Z']
compo2=['Z']
#compo1=['Z','Z','Z','E','E','E','N','N','N']
#compo2=['Z','E','N','Z','E','N','Z','E','N']

for icompo in range(0,len(compo1)):
	jobid=1
	ComponentFirstStation=compo1[icompo]
	ComponentSecondStation=compo2[icompo]
	for istart in range(0,sublist_date):
		outputfl='CC_2014_'+ComponentFirstStation+ComponentSecondStation+'_'+str(jobid)
		fsout=open(outputfl, "w")
		outstr='#PBS -l nodes=1 \n#PBS -k oe \n#PBS -q zigone \n'
		outstr+='cd %s\n' % workdir
		outstr+='source /home/geovault-05/zigone/.login \n'
		outstr+='python2.7 correlationsMain02.py oneList %s %s %s %s %d %d %d %d\n' % (LoadDirectory, SaveDirectory, ComponentFirstStation, ComponentSecondStation, sublist_date, istart, sublist_stations, index_stations)
		fsout.write(outstr)
		jobid+=1

	subid=1
	outputrun='Run_CC_'+ComponentFirstStation+ComponentSecondStation+'.sh'
	fsout=open(outputrun, "w")
	outsub1='#!/bin/sh \n'
	outsub1+='cd %s\n' % workdir
	fsout.write(outsub1)
	for isub in range(1,366):
		#outsubi1='#!/bin/sh \n'
        	#outsub+='cd  %s\n' % workdir
        	outsub='qsub CC_2014_%s%s_%d\n' % (ComponentFirstStation, ComponentSecondStation, isub)
        	subid=1
		fsout.write(outsub)
