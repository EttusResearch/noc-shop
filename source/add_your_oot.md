# Adding your RFNoC Blocks to the Noc Shop

If you built an RFNoC out-of-tree module with some blocks that you would like
to share with the RFNoC community, follow these steps to add them to the list:

1. Fork [this repository on Github](https://github.com/EttusResearch/noc-shop/fork) and check it out.
2. Navigate to your local copy of the Noc Shop and add a new branch for your
   OOT module, e.g., by running `git checkout -b my_oot_module`.
2. Run the `add_your_oot.py` script at the top level. It will create a YML
   file under `site_gen/sources/your_new_oot.yml`. You may edit this file to
   check everything is correct.
3. Submit a pull request against the [Noc Shop main repository](https://github.com/EttusResearch/noc-shop).
4. That's it! The Noc Shop owners will review your request and if appropriate,
   merge your PR which will then include your OOT module in the Noc Shop.


Please note that OOTs may be removed from the Noc Shop at any time.
