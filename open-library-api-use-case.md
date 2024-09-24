# Table of Contents
1. [Open Library API: A Use Case](#open-library-api-a-use-case)
1. [Terminology](#terminology)
1. [Use Case](#use-case)
1. [The Open Library Search API](#the-open-library-search-api)
   1. [Query Parameters Summary](#query-parameters-summary)
   1. [Query parameter q={QUERY}](#query-parameter-qquery)
   1. [Query parameter fields={FIELDS}](#query-parameter-fieldsfields)
   1. [Query parameter sort={SORT}](#query-parameter-sortsort)
   1. [Query parameter limit={LIMIT}](#query-parameter-limitlimit)
1. [Open Library Books API](#open-library-books-api)
1. [Open Library Covers API](#open-library-covers-api)
1. [Putting All Together](#putting-it-all-together)

# Open Library API: A Use Case
The Open Library API is a powerful tool for retrieving book metadata from the vast Open Library database. With this API you can search for books by title, author, ISBN, and more. You can retrieve detailed information about books, including its title, author, publisher, page count, cover image, and so much more.

This knowledge document will discuss three APIs in the context of a practical use case:

* [Search](https://openlibrary.org/dev/docs/api/search) API:  the all-encompasing search API that can return data for multiple books based on powerful search criteria
* [Books](https://openlibrary.org/dev/docs/api/books) API: for returning book-specific information like title, page count, etc
* [Covers](https://openlibrary.org/dev/docs/api/covers) API: for fetching images of book covers

> [!NOTE]
> Style Conventions Within This Document
> 
> In pre-formatted text describing API calls:
>  * items denoted in square bracket delimiters `[ ]` are optional.
>  * items denoted in curly brace delimiters `{ }` are placeholders.

# Terminology
The Open Library APIs, such as the `Search` API, provide information about *Works* and *Editions* of books.

* An *Edition* is a specific book, e.g. a book denoted by a specific ISBN

* A *Work* is a logical collection of one or more similar editions

*Work* metadata will include general umbrella information that is common to all of the editions, such as the author(s) name, first year published, average number of pages, and Dewey Decimal Classification.

*Edition* metadata will include book-specific information.

# Use Case
A practical use case for the Open Library API is to:

1. Given a list of ISBN numbers as input, search for those corresponding books using the Search API.

2. Use the Search API to Find suggested books by the same author and in the same genre as those books in the input set. Limit of 3 suggestions for each author/genre pair.

3. Extract and record interesting Work and Edition metadata for the for all books in the input and suggested set. Metadata we are interested in includes:
   * Work
      * Work ID
      * Author Name
      * Author ID
      * First Publish Year
      * Median Number of Pages
      * Dewey Decimal Classification
   
   * Edition
      * Title
      * Cover ID
      * ISBN

4. Find additional Edition-specific metadata for all books in the input and suggested set using the Books API. Metatdata we are interested in includes:
   * Exact Page Count

5. Download book cover art for all books in the input and suggested set using the Covers API.

Additional constraints:
   * Make as few API calls as possible.
   * Covers and Books API calls are invoked to return JSON data for further processing.

The crux of the work will be done by the Search API.

# The Open Library Search API
The Search API is feature-rich and offers very powerful search functionality. For the purposes of this document and use case the focus will be on those facets that are necessary for the use case.  For the full Search API documentation, which is continuously evolving, please visit [the official documentation](https://openlibrary.org/dev/docs/api/search).

The general format of the URL for a Search API request is:
```
   
   http://openlibrary.org/search.json?q={QUERY}[&fields={FIELDS}][&sort={SORT}][&limit={LIMIT}]

```
| Allowed HTTP Methods | Response Content Type | Response Codes |
| --- | --- | --- |
| `GET` | `application/json` | 200 if OK, non-200 if error |

**Response Data Characteristics**

By default, the Search API returns metadata for Works; however, based on the `{FIELDS}`, it can also return data about Editions related to those Works.  It can return multiple books in a single call, making it a great tool for getting the most data with fewest API calls.

Successful responses are in JSON format.  Example response showing Work and Edition metadata:

   ```json
   {
      "numFound": 1,
      "start": 0,
      "numFoundExact": true,
      "docs": [
         {
            "author_key": [
               "OL228319A"
            ],
            "author_name": [
               "Robert Sedgewick"
            ],
            "first_publish_year": 1990,
            "key": "/works/OL1907096W",
            "number_of_pages_median": 657,
            "ddc_sort": "005.133",
            "editions": {
               "numFound": 1,
               "start": 0,
               "numFoundExact": true,
               "docs": [
                  {
                     "key": "/books/OL2214090M",
                     "title_sort": "Algorithms in C",
                     "cover_i": 135046,
                     "isbn": [
                        "0201514257",
                        "9780201514254"
                     ]
                  }
               ]
            }
         }
      ],
      "num_found": 1,
      "q": "(isbn:0201514257)",
      "offset": null
   }
   ```
> [!NOTE]
> The outer `docs` array in the response contains Work metadata and is referred to as the "Work-level" of the response data.  The inner `docs` array contained Edition metadata and is referred to as the "Edition-level" of the response.

**Notable Response JSON Attributes**

The following JSON attributes are notable for the particular use case described in this document.

| Name (jq path) | Type | Level | Description |
| --- | --- | --- | --- |
| `.numFound` | number | Work | Number of Works found by the query before the `fields` parameter (if any) was applied |
| `.docs` | array | Work | Array of Work objects. Check the length of this to see the actual number of Works returned after `fields` were applied. |
| `.docs[].author_key` | array | Work | Author IDs |
| `.docs[].author_name` | array | Work | Author Names |
| `.docs[].first_publish_year` | number | Work | First year the work was published |
| `.docs[].key` | string | Work | "Works" API endpoint for this work; last part of path is the Work ID |
| `.docs[].number_of_pages_median` | number | Work | Median number of pages across all editions of this Work |
| `.docs[].ddc_sort` | string | Work | Dewey Decimal Classification |
| `.docs[].editions.docs` | array | Edition | Array of Editions objects. Check the length to see number of Editions returned. |
| `.docs[].editions.docs[].key` | string | Edition | "Books" API endpoint for this Editions; last part of the path is the Book ID |
| `.docs[].editions.docs[].title_sort` | string | Edition | Edition's title |
| `.docs[].editions.docs[].cover_i` | number | Edition | Edition's Cover ID (for use with Covers API) |
| `.docs[].editions.docs[].isbn` | array | Edition | ISBN10 and ISBN13 identifiers for this Edition |

## Query Parameters Summary
| Parameter Name | Description | Required |
| :--- | :--- | :---: |
| q | This is the search query.  Its value `{QUERY}` specifies Work or Edition field:value pairs or a logical expression defining the search criteria. | Yes |
| fields | This is a field specification. Its value `{FIELDS}` specifies which Work or Edition fields to return in the respone. | No |
| sort | Sorting method. It's value `{SORT}` specifies how to sort the results. | No |
| limit | Limit the results to no more than `{LIMIT}` items. Must be greater than zero. | No |

**HTTP Characteristics**:


### Query parameter q={QUERY}
The `{QUERY}` value of the `q` query parameter is an expression describing Works or Editions to search for. In its simplest form, the expression is a single `field:value` pair such as `isbn:0201514257`
```
   
   https://openlibrary.org/search.json?q=isbn:0201514257

```
This would return a plethora of metadata about the *Work* associated with ISBN 0201514257 -- but not any *Edition* metadata.

> [!NOTE]
> Recall that the Search API returns metadata for Works by default. To return Edition metadata also, a `fields` parameter must be used.  More on this later.

There are many possible fields to use in a `{QUERY}` and correspondingly in the `{FIELDS}`. `{QUERY}` fields needed for this use case include:

| Field | Description |
| :--- | :--- |
| `isbn` | ISBN10 or ISBN13 book identifier |
| `ddc_sort` | Dewey Decimal Classification |
| `author_key` | Author Identifier |
| `title_sort` | Book title |

Logical operators `AND`, `OR`, and `NOT` can be used to form complex query expressions of multiple field:value pairs, or of multiple values of a single field. Parenthesis can be used for grouping.  Examples:

| Expression | Description |
| --- | --- |
| `isbn:0201514257` | Search for ISBN 0201514257 |
| `(isbn:0201514257)` | Same as above |
| `isbn:(0201514257)` | Same as above |
| `isbn:(0201514257 OR 9781565927605 OR ... )` | Search for multiple ISBNs at once|
| `author_key:9781565927605 AND NOT ddc_sort:005.133` | Search for works by author ID OL228319A not in Dewey Decimal class 005.133 |

> [!WARNING]
> When constructing the value of the `{QUERY}` programmatically it's imperative to urlencode the string. To be clear, only the value of the `q` query parameter need be urlencoded when constructing the full URL for the Search API call. This is because the search string could have sensitive metacharacters within it.

:bulb: As you can see, the logical OR'ing of ISBN numbers is a great way to get data for multiple books in one API call. It is ideal for this use case.

### Query parameter fields={FIELDS}
The `{FIELDS}` value of the optional `fields` query parameter is a comma-separated list of Work-level and Edition-level fields to return in the JSON response.  The Search API returns a lot of data by default, much of which is not needed in this use case.  The `fields` query parameter is used to limit it.  Possible field names can be derived from the JSON attributes as seen in the objects at the Work-level of a response, as well as those at the Edition-level. Consider the example JSON:

   ```json
   {
      "numFound": 1,
      "start": 0,
      "numFoundExact": true,
      "docs": [
         {
            "author_key": [
               "OL228319A"
            ],
            "author_name": [
               "Robert Sedgewick"
            ],
            "first_publish_year": 1990,
            "key": "/works/OL1907096W",
            "number_of_pages_median": 657,
            "ddc_sort": "005.133",
            "editions": {
               "numFound": 1,
               "start": 0,
               "numFoundExact": true,
               "docs": [
                  {
                     "key": "/books/OL2214090M",
                     "title_sort": "Algorithms in C",
                     "cover_i": 135046,
                     "isbn": [
                        "0201514257",
                        "9780201514254"
                     ]
                  }
               ]
            }
         }
      ],
      "num_found": 1,
      "q": "(isbn:0201514257)",
      "offset": null
   }
   ```

Each object at the Work-level (outer `docs` array) has an attribute named `key` which denotes the Work identifier.  To return just that field in the JSON response we'd use a query contructed thusly:
```
https://openlibrary.org/search.json?q=isbn:0201514257&fields=key
```
This returns:
```json
{
  "numFound": 1,
  "start": 0,
  "numFoundExact": true,
  "docs": [
    {
      "key": "/works/OL1907096W"
    }
  ],
  "num_found": 1,
  "q": "isbn:0201514257",
  "offset": null
}
```

Notice how only the `key` attribute for the Work is returned.  Where's the Edition information? We have to ask for it. Specify the `editions` field, in addition to the `key` field, to get the information about the Work and its Editions in the same response.

```
https://openlibrary.org/search.json?q=isbn:0201514257&fields=key,editions
```

This returns:
```json
{
  "numFound": 1,
  "start": 0,
  "numFoundExact": true,
  "docs": [
    {
      "key": "/works/OL1907096W",
      "editions": {
        "numFound": 2,
        "start": 0,
        "numFoundExact": true,
        "docs": [
          {
            "key": "/books/OL2214090M"
          }
        ]
      }
    }
  ],
  "num_found": 1,
  "q": "isbn:0201514257",
  "offset": null
}
```

Wait? Where's the rest of the Edition data? Didn't we just ask for the whole "editions" field and corrsponding object? Yes, however the Work and the Edition both have a field named `key`. Since `key` was specified as a field selector it was applied to the Work *AND* the Edition. This is true for a number of field names that the Work and Edition objects have in common, like `title_sort`, `isbn` and so forth.

Specifying only Work-level field names to get fields in the Work and Edition isn't ideal because it produces redundant data.  For example, if the field specifier is `key,editions,isbn` you'll get a list of *ALL* ISBNs for that Work at the Work-level, and then the Edition-specific ISBN at the Edition-level.  The latter is usually what you want, and it is what we want in this use case.

An example of this extra, redundant data is ths following:
```
https://openlibrary.org/search.json?q=isbn:0201514257&fields=key,editions,isbn
```
Which returns:
```json
{
  "numFound": 1,
  "start": 0,
  "numFoundExact": true,
  "docs": [
    {
      "isbn": [
        "0201350882",
        "9780201361186",
        "0201510596",
        "9780201314526",
        "0201514257",
        "0201314525",
        "0201361183",
        "9780201350883",
        "9780201514254",
        "9780201510591"
      ],
      "key": "/works/OL1907096W",
      "editions": {
        "numFound": 2,
        "start": 0,
        "numFoundExact": true,
        "docs": [
          {
            "key": "/books/OL2214090M",
            "isbn": [
              "0201514257",
              "9780201514254"
            ]
          }
        ]
      }
    }
  ],
  "num_found": 1,
  "q": "isbn:0201514257",
  "offset": null
}
```

It is possible to select Edition-specific fields like `edition.{field_name}`.  In order to get Edition-specific fields, you must use a `{FIELDS}` value that:

1. Specifies `key` to select the Work.
1. Optionally specifies any other desired `{field_name}` to select additional Work fields.
1. Specifies `editions` to select the Editions object within that Work.
1. Specifies `editions.key` to select the Edition.
1. Specifies `editions.{field_name}` (1 or more) to select those specific Edition fields.

So to improve the above ISBN example, we'd use a field specification like: `key,editions,editions.key,editions.isbn` thusly:
```
https://openlibrary.org/search.json?q=isbn:0201514257&fields=key,editions,editions.key,editions.isbn
```
Which returns:
```json
{
  "numFound": 1,
  "start": 0,
  "numFoundExact": true,
  "docs": [
    {
      "key": "/works/OL1907096W",
      "editions": {
        "numFound": 2,
        "start": 0,
        "numFoundExact": true,
        "docs": [
          {
            "key": "/books/OL2214090M",
            "isbn": [
              "0201514257",
              "9780201514254"
            ]
          }
        ]
      }
    }
  ],
  "num_found": 1,
  "q": "isbn:0201514257",
  "offset": null
}
```
This is much more managable.

<a name="use-case-fields"></a>
The full list of `{FIELDS}` that we need for this use case is:
| Field | Level | Descsription |
| --- | --- | --- |
| `key` | Work | Work ID |
| `author_key` | Work | Author ID(s) |
| `author_name` | Work | Author name(s) |
| `first_publish_year` | Work | First publish year |
| `ddc_sort` | Work | Dewey Decimal Classification |
| `number_of_pages_median` | Work | Median number of pages across all Editions |
| `editions` | Work | Editions object |
| `editions.key` | Edition | Book ID |
| `editions.title_sort` | Edition | Book title |
| `editions.isbn` | Edition | Book ISBN |

### Query parameter sort={SORT}
For this use case, when searching for suggestions it's ideal to sort the results by book rating.  Therefore the only meaningful value for this parameter is `rating` which will sort the results in descending order (highest rated first).  Example:
```
https://openlibrary.org/search.json?q=ddc_sort:005.133&fields=key,ratings_average&sort=rating&limit=4
```
Which returns:
```json
{
  "numFound": 3373,
  "start": 0,
  "numFoundExact": true,
  "docs": [
    {
      "ratings_average": 4.428571,
      "key": "/works/OL3267304W"
    },
    {
      "ratings_average": 4.5,
      "key": "/works/OL15444205W"
    },
    {
      "ratings_average": 4.2,
      "key": "/works/OL2685843W"
    },
    {
      "ratings_average": 4.2222223,
      "key": "/works/OL53184W"
    }
  ],
  "num_found": 3373,
  "q": "ddc_sort:005.133",
  "offset": null
}
```

### Query parameter limit={LIMIT}
`{LIMIT}` is an integer specifying the max number of results to return in the response data.  For this use case it is used when searching for suggestions to limit the number of books to 3.

# Open Library Books API
The Book API is used for finding Book-specific metadata.  For the full Books API documentation, which is continuously evolving, please visit [the official documentation](https://openlibrary.org/dev/docs/api/books).

The general format of the URL for a Books API request, for the purposes of this use case, is:
```
   
   http://openlibrary.org/books/{BOOK_ID}.json

```
| Allowed HTTP Methods | Response Content Type | Response Codes |
| --- | --- | --- |
| `GET` | `application/json` | 200 if OK, non-200 if error |

`{BOOK_ID}` in the request URL is the ID of the book, as could be determined by the Search API previously discussed. Specifically the `{BOOK_ID}` is derived from the `editions.key` at the Editions-level of a search response, where the `{BOOK_ID}` is the last path component of that value.  For example, consider the search query:

```
https://openlibrary.org/search.json?q=isbn:0201514257&fields=key,editions,editions.key
```
Which returns:
```json
{
  "numFound": 1,
  "start": 0,
  "numFoundExact": true,
  "docs": [
    {
      "key": "/works/OL1907096W",
      "editions": {
        "numFound": 2,
        "start": 0,
        "numFoundExact": true,
        "docs": [
          {
            "key": "/books/OL2214090M"
          }
        ]
      }
    }
  ],
  "num_found": 1,
  "q": "isbn:0201514257",
  "offset": null
}
```
The `{BOOK_ID}` is `OL2214090M` as derived from the value of the Edition-level `key` field.

Now a Books API call can be made like:
```
https://openlibrary.org/books/OL2214090M.json
```
This returns a lot of metadata about the book, most of which we don't need for this use case. The *ONLY* field we need for this use case is `number_of_pages` which gives the exact number of pages for that book.  Contrast that with the `number_of_pages_median` of a Work which is the median number of pages across all Editions of that Work; unless there's only one book in the Work, `number_of_pages_median` and `number_of_pages` very likely will be different.

Making an API call just to get the number of pages is expensive: it's an entire addtional API call for one value! If you are needing to keep the API calls to an absolute minimum, you could:
* Suffice and use the `number_of_pages_median` as the page count for a given book. It may not be exact but it should be close!
* Look at `editions.numFound` at the Edition-level. If it is exactly 1 you can be confident that the book's `number_of_pages` is the same as `number_of_pages_median` at the Work-level, and avoid the extra Books API call to get the page count.

# Open Library Covers API
The Covers API is used for finding Book-specific cover data in JPEG format.  For the full Covers API documentation, which is continuously evolving, please visit [the official documentation](https://openlibrary.org/dev/docs/api/covers).

The general format of the URL for a Covers API request, for the purposes of this use case, is:
```
   
   http://covers.openlibrary.org/b/id/{COVER_ID}-{SIZE}.jpg

```
| Allowed HTTP Methods | Response Content Type | Response Codes |
| --- | --- | --- |
| `GET` | `image/jpeg` | 200 if OK, non-200 if error |

`{COVER_ID}` in the request URL is the Cover ID of the book, as could be determined by the Search API previously discussed. Specifically the `{COVER_ID}` is derived from the `editions.cover_i` at the Edition-level of a search response.  Consider the following search query:
```
https://openlibrary.org/search.json?q=isbn:0201514257&fields=key,editions,editions.cover_i
```
Which returns:
```json
{
  "numFound": 1,
  "start": 0,
  "numFoundExact": true,
  "docs": [
    {
      "key": "/works/OL1907096W",
      "editions": {
        "numFound": 2,
        "start": 0,
        "numFoundExact": true,
        "docs": [
          {
            "cover_i": 135046
          }
        ]
      }
    }
  ],
  "num_found": 1,
  "q": "isbn:0201514257",
  "offset": null
}
```

`{COVER_ID}` for this book is `135046`.

`{SIZE}` specifies the desired relative size of image to retrieve. It is one of `S`, `M`, or `L` only. Note the following:
* `S` (small) is often unusuable because the images are very small by modern standards.
* `M` (medium) is more usable and preferred.
* `L` (large) is better quality than medium; however, retieving large images often required TWO requests per call: the initial Covers API request and a redirect to actually fetch the image. If conserving API calls is necessary, fetching Large images is not ideal.

To download the medium-sized image, make a GET request to:
```
https://covers.openlibrary.org/b/id/135046-M.jpg
```

# Putting All Together
Now that you know more about the Open Library Search, Books, and Covers APIs in the context of this [use case](#use-case) you can find book metadata about initial ISBNs, find suggestions based per author and genre combination, and download cover data -- all with minimal API calls. Here's how to go about it:

1. Establish your initial set of input ISBNs. They can be ISBN10 or ISBN13 flavors.
2. Execute the Search API to find data about those books with one call! You do this by logically OR'ing the ISBN values in the `{QUERY}` value. Be sure to set the `fields` query parameter to select the fields needing, as [discussed earlier](#use-case-fields). The query parameters should be like (this is a long line, scroll right as needed):
```
q=isbn:(ISBN1 OR ISBN2 OR ... OR ISBNN)&fields=key,author_key,author_name,first_publish_year,ddc_sort,number_of_pages_median,editions,editions.key,editions.title_sort,editions.isbn
```
3. For each Work in the response, save the desired Work-level and Edition-level metadata to some cache object index by ISBN.
4. For each `author_key` and `ddc_sort` combination, execute a new search for that author and DDC combination, with a limit of 3. You may need to take care to exclude books you've alreay retreived by using a `NOT` expression in your `{QUERY}`. For example, you can gather the titles from your already-retrieved book data and create a NOT'd expression to use in the suggestion search (this is a long line, scroll right as needed):
```
q=author_key:AUTHKEY AND ddc_sort:DDC AND NOT title_sort:(TITLE1 OR TITLE2 OR ... OR TITLEN)&fields=key,author_key,author_name,first_publish_year,ddc_sort,number_of_pages_median,editions,editions.key,editions.title_sort,editions.isbn
```
Update your cache object with the desired Work-level and Edition-level metdata.
5. If exact number of pages is needed you can iterate over your books in your cache object and use the Edition key (Book ID) in a call to the Books API to get the exact page count. Note that this will cost an extra API call per book!
6. Iterate over your books in your cache object and use the Cover ID to make a call to the Covers API to pull the medium image.
7. Write the book metadata from your cache object in whatever format you desire (CSV, etc).


An example implementation written in Python is available here.  The script requires the Python `requests` module which you can install with `pip` in your Python environment.  Execute the script without any arguments for further information about what it does and how to run it. :warning: The script is a proof-of-concent only and is entirely unsupported.

[Open Library API POC](ol-poc.py)
