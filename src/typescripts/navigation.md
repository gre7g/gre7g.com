Navigation
==========

The application navigates by replacing the URL by calling `history.pushState()` and `history.replaceState()`. To keep on
top of what is pushed, I'm documenting the supported paths here:

Paths:

- / or any unrecognized string

- /books/<product_id>

  Product listing for the item.

- /shop

  Generally the same a / but with less about information

- /appearances
- /contact
- /about
- /user/profile
- /user/logout
- /cart
- /privacy
- /sitemap

Also
----
The following paths are also supported:

- /static/styles.css
- /static/images/*
- /src/typescripts/*.js
