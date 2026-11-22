TODO
====

Although I write down TODO items in the code as I think of them, I thought it might be nice to have a centralized file
for tracking tasks, subtasks, and anything else that's more project-oriented.

High Urgency
------------
- [ ] Need digital downloads:
  - [ ] Skeleton Crew audiobook
  - [ ] Small World audiobook
  - [ ] Fair Trade audiobook
  - [ ] Reaper's Lottery audiobook
  - [ ] Executioner's Gambit audiobook
  - [ ] Long Way Home audiobook
  - [ ] Tales of Hayven Celestia I audiobook
- [ ] Hide thumbnails when there's only one
- [ ] Show out of stock message as needed

Moderate Urgency
----------------
- [ ] Is everything logged on purchase completion (like fees)?
- [ ] Bugs found while writing TypeScript tests (each has a `test.fails` test -- drop the `.fails` once fixed):
    - [ ] Status bar never reappears after being closed (`show_*()` don't call `.show()`)
    - [ ] Cart summary flickers: `.toggle(G_CART.contents.length)` passes a number, which jQuery treats as a duration
    - [ ] Carousel keeps the previous product's image when a product has no images
- [X] Need all the images

Basic Features
--------------
- [ ] Check dynamically added HTML for links. They need to be intercepted and handled via TS navigation.
- [ ] Test narrow and on phone
- [ ] Links for other places an item is available

Low Urgency
-----------
- [ ] Deactivated accounts
- [ ] In the dispatch script, I have a check that won't treat "No changes to deploy." as an error. However, if I have to
      re-execute a deploy command because we weren't logged in, then I still treat the "No changes to deploy." status as
      an error.
- [ ] Add code coverage for TypeScript
- [ ] Breadcrumbs -- see breadcrumbs-feature branch for visual component, but let's work on adding the data as we go
- [ ] Show a sitemap
- [ ] Try out that script experiment in notes/suggested_console.py

Old and Completed
-----------------
- [X] TypeScript unit tests
- [X] Go through .ts files and add more comments, function headers, etc.
- [X] Carousel
- [X] Products with children shouldn't show the add to cart button
- [X] When cart is empty, hide the subtotal
- [X] Theme the login to match -- see notes/managed-login-theming.md
- [X] Profile menu is lower case
- [X] Upload product images
- [X] Add a configuration switch that pulls down managed login
- [X] Add a push of managed login to s3
- [X] hash must include managed login JSON
- [X] "Skeleton Crew" paperback entry is missing text
- [X] When pulling up the / page, there should be more before the products, so write some!
- [X] On vacation
- [X] User profile page
- [X] Books link needs to drop-down menu
- [X] Shopping cart items must link to listings
- [X] Single order page is broken
- [X] Orders page login button is broken
- [X] Orders page is very broken and should show a message if you're not logged in
- [X] Contact must disable the button until the fields are entered
- [X] Sending an email on the local simulation scrolled an error on the console but returned a 201
- [X] Profile link is no longer working
- [X] Local links like appearances need to be intercepted and handled via TS navigation. There's probably quite a few of
  these, so be thorough.
- [X] Empty shopping cart should show a message and disable the checkout button
- [X] Appearances should be the same width as the other sections
- [X] MCFC needs an image
- [X] Test the status bar
- [X] CSS
- [X] Python unit tests
- [X] Add code coverage for Python
- [X] Add something to monitor progress on code coverage
- [X] Show previous orders (logged in only)
- [X] Checkout must show quantity and extended amount
- [X] Handle AJAX errors
- [X] Move message bar to one consistent location
- [X] Sign in if signed out, profile if signed in
- [X] Show contact form
- [X] Show privacy policy
- [X] Shopping cart needs:
    - [X] Quantity
    - [X] price per
    - [X] remove from cart
    - [X] update amount
- [X] e-mail the administrator if we are unable to decrement the inventory quantities in confirm_order.py
- [X] Show shop
- [X] Log out
- [X] Thank you screen showing a summary and downloads
- [X] Show AI policy
- [X] Show upcoming appearances
- [X] Show about the author
- [X] Show current order and any downloads
- [X] Create another static analysis for the template file to check if there are permissions, timeouts, and environment
      variables available to the functions. Could even re-sort the items? Could we put decorators or comments on
      functions to identify which resources they require?
- [X] The products database entries should contain a description field that is longer than the item name but shorter
      than the HTML description that we have in the current description field. PayPal wants something for an item
      description, and it doesn't like the length and mark-up.
- [X] Stop using secrets manager for password generation and do it yourself
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
