.. _technical_requirements:


Software requirements
=====================

=======================  ==============
Software/framework       Version        
-----------------------  --------------
Python                   3.10
PostgreSQL               9.6+  
Node                     13
=======================  ==============

The current python dependencies can be found in github repository zac/backend/requirements/production.txt.
The current node dependencies can be found in github repository zac/backend/package.json.


Hardware requirements
=====================

Currently in our production implementation we have ~50 concurrent users and run the following
kubernetes settings:

=======================  ===============
Resource                 Values        
-----------------------  ---------------
ZAC-Backend
-----------------------  ---------------
CPU: requests            1             
CPU: limits              1
Memory: requests         2Gi
Memory: limits           2Gi
Storage                  Default
Replica count            2
-----------------------  ---------------
Redis
-----------------------  ---------------
CPU: requests            Default             
CPU: limits              Default
Memory: requests         Default
Memory: limits           Default
Storage                  Persistent 12Gi
Replica count            1
=======================  ===============
