TODO
====

Although I write down TODO items in the code as I think of them, I thought it might be nice to have a centralized file
for tracking tasks, subtasks, and anything else that's more project-oriented.

High Urgency
------------
- [ ] Thank you screen showing a summary and downloads

Moderate Urgency
----------------
- [ ] The products database entries should contain a description field that is longer than the item name but shorter 
      than the HTML description that we have in the current description field. PayPal wants something for an item
      description, and it doesn't like the length and mark-up.
- [ ] e-mail the administrator if we are unable to decrement the inventory quantities in confirm_order.py

Basic Features
--------------
- [ ] Show shop
- [ ] Show upcoming appearances
- [ ] Show contact form
- [ ] Show about the author
- [ ] Log out
- [ ] Show privacy policy
- [ ] Show a sitemap
- [ ] Shopping cart needs:
  - [ ] Quantity, price per, remove from cart, update amount
- [ ] Show current order and any downloads
- [ ] Show previous orders (logged in only)

Low Urgency
-----------
- [ ] In the dispatch script, I have a check that won't treat "No changes to deploy." as an error. However, if I have to
      re-execute a deploy command because we weren't logged in, then I still treat the "No changes to deploy." status as
      an error.
- [ ] Add code coverage for Python
- [ ] Add code coverage for Typescript
- [ ] Add something to monitor progress on code coverage
- [ ] Go through .ts files and add more comments, function headers, etc.
- [ ] Create another static analysis for the template file to check if there are permissions, timeouts, and environment
      variables available to the functions. Could even re-sort the items? Could we put decorators or comments on 
      functions to identify which resources they require?
- [X] Stop using secrets manager for password generation and do it yourself

Old and Completed
-----------------
- [X] URL history is broken (at least on cloud)
- [X] Don't allow customers to buy physical items with a shipping country other than US
- [X] Is the audit log working on a thread?
- [X] 419 error on PUT resulted in a follow-up GET!
- [X] Refactor gre7g_util into lambda and database utilities
- [X] Does code= get removed from the URL after login?
- [X] Managed login
- [X] Switch internal/external link modification over to navigation interception
- [X] First POST to guest isn't triggering a retry. I think it's returning a 403 instead of 417.
- [X] Delete old .js files in s3
- [X] Split library between app and testing modules.
