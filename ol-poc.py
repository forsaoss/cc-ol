#!/usr/bin/env python3
import json
import requests
import sys
import csv

###
###
### User-Modifiable Feature Flags
###
###
# g_want_exact_pages : bool
# If you want to find the exact number of pages for a given book, set this to
# True.  However this will elicit an additional API call for each individual
# book that was found by the input search and the suggestion search.
#
# When this is set to False the additional API call is skipped, however the
# exact number of pages will not be known.
#
# In either case, the code will retrieve the 'number_of_pages_median' field
# from the relevant works. This number indicates the median number of pages
# accross all editions of a work, and may suffice as indicator of the
# approximate page count for a given book.
g_want_exact_pages = True


#######################################
###
### NO NEED TO EDIT ANYTHING ELSE BELOW
###
#######################################


###
### GLOBALS
###
# Base URLs for our API calls.
# g_base_cover_url : str
#   For getting book cover pictures.
# g_base_url : str
#   For all other OpenLibrary API calls.
g_base_cover_url = 'http://covers.openlibrary.org'
g_base_url = 'https://openlibrary.org'

# g_api_session : requests.sessions.Session
# API requests session object for use throughout the code.
g_api_session = None

# g_arg_isbn_list : dict
# A dictionary of ISBNs we searched for and found, indexed by ISBN number,
# specifically a string of the format "ISBN10/ISBN13".  This will hold the
# retrieved data for their respective ISBNs.  Note that we'll be adding a
# 'type' field, with string value either 'input' or 'suggestion, to the data
# for each ISBN. This indicates whether the book was found by the initial
# search against the input ISBNs or was found as a suggestion.
g_arg_isbn_list = None

# g_total_api_calls : int
# To track total number of API calls made to endpoints at the g_base_url and
# g_base_cover_url noted above.
g_total_api_calls = 0

# g_title_field : str
# Experimental to see the differences between using 'title' vs 'title_sort'
g_title_field = 'title_sort'

# g_ol_search_fields : list
# Set of search fields we're interested in for the calls to be made to the
# 'search.json' endpoint of the API. We want certain fields for the overall
# work as well as the editions.
g_ol_search_fields = [
    'key',                          # work ID
    'author_key',                   # work's author ID
    'author_name',                  # work's author name
    'first_publish_year',           # work's first publish yeah
    'ddc_sort',                     # work's ddc (Dewey Decimal Classification) number
    'number_of_pages_median',       # work's median number of pages
    'editions',                     # the edition's object
    f'editions.{g_title_field}',    # edition's title
    'editions.cover_i',             # edition's cover ID
    'editions.key',                 # edition's ID -- used to get extact page count
    'editions.isbn',                # edition's ISBN(s)
    'editions.language'             # edition's language
]

###
### HELPER FUNCTIONS
###
def burl(p):
	return f'{g_base_url}/'+p

def curl(p):
	return f'{g_base_cover_url}/'+p

def paren(s):
    return f'({s})'

def logic_join(things,op='OR'):
    n = len(things)
    if n == 0:
        return ''
    logic = f' {op} '.join(things)
    # No need to put parens around single items.
    return (paren(logic) if n > 1 else logic)

def unique_list(x):
    y = []
    [y.append(i) for i in x if i not in y]
    return y

# Finds the first element in common between two lists and returns it. Returns
# None if there are no common elements.
def first_in_common(a,b):
    if a == None or b == None:
        return None
    for x in a:
        for y in b:
            if x == y:
                return x
    return None

###
### PROGRAM USAGE AND ARG VALIDATION FUNCTIONS
###
def usage():
    print("Usage: ol-poc.py ISBN [ISBN ...]")
    print("""
Lookup book information using the OpenLibrary APIs.

At least one ISBN number must be provided as an argument.

ISBNs can be either 10- or 13-digit flavors, or a combination thereof.

Any duplicate ISBN numbers provided will be discarded.

Book metadata will be written to 'output.csv' in the current directory.
Book covers will be downloaded to the current directory.

If exact page counts are required, edit the script and change
'g_want_exact_pages' to True. By default this is False and only median page
count is retreived.

For general information about the APIs, see the official docs at
https://openlibrary.org/developers/api
""")

# Ensure CLI arguments are numbers that are 10 or 13 digits long.
def validate_cli_args():
    all_lens = []
    for x in sys.argv[1:]:
        if not x.isdigit():
            return False
        all_lens.append(len(x))
    for x in all_lens:
        if (x not in [10,13]):
            return False
    return True

def get_opts():
    global g_arg_isbn_list
    if len(sys.argv) < 2:
        usage()
        exit(0)
    if not validate_cli_args():
        print("Invalid input: expecting one or more 10- or 13-digit ISBN numbers",file=sys.stderr)
        print("Execute this program with no arguments for more information.",file=sys.stderr)
        exit(2)
    g_arg_isbn_list = unique_list(sys.argv[1:])
    return True

###
### API SESSION FUNCTIONS and SEARCH FUNCTIONS
###

def init_api_session():
	global g_api_session
	g_api_session = requests.Session()

def ol_search(query_params, limit=''):
    global g_total_api_calls
    field_params = ','.join(g_ol_search_fields)
    if limit != '': limit=f'&limit={limit}'
    qp_quoted = requests.utils.quote(f'{query_params}')
    q = f'q={qp_quoted}&fields={field_params}{limit}'
    g_total_api_calls += 1
    #print(q+"\n")
    return g_api_session.get(burl(f'/search.json?{q}'))

def ol_book(book_key):
    global g_total_api_calls
    g_total_api_calls += 1
    return g_api_session.get(burl(f'/book/{book_key}.json'))


def find_related_suggestions(item,sugg_list):
    ls = []
    item_isbn = list(item.keys()).pop()
    item_data = item[item_isbn]
    item_ddc = item_data.get('ddc_sort')
    if item_ddc == None: return ls
    item_author = item_data.get('author_key')
    for x in sugg_list:
        sugg_isbn = list(x.keys()).pop()
        sugg_data = x[sugg_isbn]
        sugg_ddc = sugg_data['ddc_sort']
        sugg_author = sugg_data['author_key']
        if sugg_ddc != item_ddc: continue
        if first_in_common(item_author,sugg_author) != None:
            ls.append(x)
    return ls

def output_items(isbn_cache):
    input_list = []
    sugg_list = []
    # Find all the books we found per the provided CLI input list.
    # Seperate this data into its own list.
    for x in isbn_cache['data']:
        data = isbn_cache['data'][x]
        if data['type'] == 'input':
           input_list.append({ x : data})
    # Find all the suggestions. Seperate this data into its own list.
    for x in isbn_cache['data']:
        data = isbn_cache['data'][x]
        if data['type'] == 'suggestion':
           sugg_list.append({ x : data})
    fp = open("output.csv", "wt")
    writer = csv.writer(fp, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
    writer.writerow(["ISBN10/ISBN13","Title","Author(s)","First Year Published","Pages (median)","Pages","Type","Work","Language","Book"])
    for x in input_list:
        write_item(x,writer)
        y = find_related_suggestions(x,sugg_list)
        for z in y: write_item(z,writer)
    fp.close()

def write_cover_txt(pair,base,txt):
    filename = base + ".txt"
    fp = open(filename, "wt")
    fp.write(txt+"\n")
    fp.close()

def write_cover(res,pair,base):
    if res.status_code != 200:
        write_cover_txt(pair,base,f'Failed API call to get cover for {pair}: status {res.status_code}.')
        return
    filename = base + ".jpg"
    fp = open(filename,"wb")
    fp.write(res.content)
    fp.close()

def download_covers(isbn_cache):
    global g_total_api_calls
    for isbn_pair in isbn_cache['data']:
        data = isbn_cache['data'][isbn_pair]
        cover_i = data.get('cover_i')
        filename_base = "-".join(isbn_pair.split("/"))
        if cover_i == "N/A":
            write_cover_txt(isbn_pair,filename_base,f'ISBN {isbn_pair} has no cover ID available by API.')
            continue
        # Download medium files only. This requires one request while large files require two (first + redirect)
        path = f'/b/id/{cover_i}-M.jpg'
        g_total_api_calls += 0 # not rate limited; don't count towards overall API count?
        res = g_api_session.get(curl(path))
        write_cover(res,isbn_pair,filename_base)


            
        
def write_item(item,writer):
    # isbn, title, author, first_year, median_pages, type, work
    row = []
    isbn = list(item.keys()).pop()
    data = item[isbn]
    row.append(isbn)
    row.append(data['title'])
    row.append(';'.join(data['author_name']))
    row.append(str(data['first_publish_year']))
    row.append(str(data['number_of_pages_median']))
    row.append(str(data['pages']))
    row.append(str(data['type']))
    row.append(str(data['work']))
    row.append(str(data['language']))
    row.append(str(data['book']))
    writer.writerow(row)

def get_cache_item(doc,t):
    global g_arg_isbn_list
    item = {
        'work': None,
        'author_key': None,
        'author_name': None,
        'ddc_sort': None,
        'first_publish_year': None,
        'number_of_pages_median': None,
        'pages': "N/A",
        'book': None,
        'title': None,
        'isbn': None,
        'cover_i': None,
        'language': None,
        'type': t
    }
    item['work'] = doc.get('key').split('/')[2]
    item['author_key'] = doc.get('author_key',['N/A'])
    item['author_name'] = doc.get('author_name',['N/A'])
    item['ddc_sort'] = doc.get('ddc_sort',None)
    item['first_publish_year'] = doc.get('first_publish_year',"N/A")
    item['number_of_pages_median'] = doc.get('number_of_pages_median',"N/A")
    item['book'] = doc.get('editions',[]).get('docs',[])[0].get('key').split('/')[2]
    item['title'] = doc.get('editions',[]).get('docs',[])[0].get(g_title_field,"N/A")
    #if t == 'init':
    #    item['isbn'] = first_in_common(g_arg_isbn_list,doc.get('editions',[]).get('docs',[])[0].get('isbn'))
    #else:
    #    item['isbn'] = doc.get('editions',[]).get('docs',[])[0].get('isbn')[0]
    item['isbn'] = doc.get('editions',[]).get('docs',[])[0].get('isbn')
    item['cover_i'] = doc.get('editions',[]).get('docs',[])[0].get('cover_i',"N/A")
    item['language'] = doc.get('editions',[]).get('docs',[])[0].get('language',['N/A'])[0]
    return item

def blank_isbn_cache():
    return {
        'code':0,
        'total':0,
        'data':{}
    }

def isbn_pair(pair):
    return '/'.join(sorted(pair))

def get_isbn_cache(q, cache=blank_isbn_cache(), t='input', limit=''):
    add_limit = 0
    num_added = 0
    if t == 'suggestion': add_limit = 3
    res = ol_search(q,limit)
    cache['code'] = res.status_code
    if res.status_code != 200:
        return cache
    data = res.json()
    if data.get('numFound',0) == 0:
        return cache
    for doc in data['docs']:
        item = get_cache_item(doc,t)
        if item.get('isbn') == None: continue
        index = isbn_pair(item.get('isbn'))
        if not index in cache['data']:
            if g_want_exact_pages:
                res = ol_book(item.get('book'))
                if res.status_code == 200:
                    data = res.json()
                    item['pages'] = data.get('number_of_pages','N/A')
            cache['data'][index] = item
            cache['total'] += 1
            num_added += 1
            if add_limit > 0 and num_added == add_limit:
                break
    #print(f'{add_limit} {num_added}')
    return cache

def get_count_by_author(isbn_cache, author_key):
    count = 0
    for isbn in isbn_cache['data']:
        data = isbn_cache['data'][isbn]
        if author_key in data.get('author_key'):
            count += 1
    return count

#def get_work_excludes(isbn_cache):
#    works = []
#    for isbn in isbn_cache['data']:
#        data = isbn_cache['data'][isbn]
#        works.append(data['work'])
#    return unique_list(works)

def get_title_excludes(isbn_cache):
    titles = []
    for isbn in isbn_cache['data']:
        data = isbn_cache['data'][isbn]
        titles.append(paren(data['title']))
    return unique_list(titles)

def get_suggested_by_ddc(isbn_cache):
    cache = {}
    current_total = isbn_cache.get('total')
    if current_total == 0:
        return cache
    for isbn in isbn_cache['data']:
        data = isbn_cache['data'][isbn]
        ddc = data.get('ddc_sort')
        authors = data.get('author_key')
        if ddc == None: continue
        cache.setdefault(ddc,[])
        #for x in authors: cache[ddc].append(x)
        cache[ddc] += authors
    ddc_list = list(cache.keys())
    if len(ddc_list) == 0:
        # This will happen if no works records had a ddc_sort field.
        return cache
    # Bang out new queries for each ddc/author pairing.
    # We want up to 3 additional books for each pair.
    for x in ddc_list:
        uniq_auth = unique_list(cache[x])
        for y in uniq_auth:
            # Apparent bug in API. Doesn't seem possible to exclude a work ID.
            # Example
            # https://openlibrary.org/search.json?q=(work:OL2836581W)
            # returns the requested work, and other unrelated works.
            # And https://openlibrary.org/search.json?q=(work:OL2836581W%20AND%20NOT%20work:OL2836581W)
            # in theory should return nothing, but it returns the work and other works as well.
            # 
            # So we'll shift to finding suggestions based on titles that we don't have yet.
            #
            #works = get_work_excludes(isbn_cache)
            titles = get_title_excludes(isbn_cache)
            q = logic_join([paren(f'ddc_sort:{x}'), paren(f'author_key:{y}')],'AND')
            #q += ' AND NOT ' + paren('work:' + logic_join(works,'OR'))
            q += ' AND NOT ' + paren(f'{g_title_field}:' + logic_join(titles,'OR'))
            #limit = get_count_by_author(isbn_cache, y) + 3
            limit = 3
            print(q)
            get_isbn_cache(q,isbn_cache,'suggestion',limit)
    return isbn_cache



###
### MAIN
###
# have_books : bool
# Convenience flag indicating the status of the initial ISBN search. Influences
# further actions taken, messages printed to the user and the exit status of
# the program.
# if have_books is True :
#   Means that the initial search returned > 0 books. Suggestion search and
#   cover download will be executed. The exit status of the program will be
#   zero.
# if have_books is False :
#   Means that the initial search returned zero books. Suggestion search and
#   cover download will be skipped. User will be informed that no books were
#   found. Exit status of the program will be non-zero.
#
# Initialized to False.
# Set to True pending the result of the initial search.
have_books = False

# Get CLI options/arguments and init our requests API session.
get_opts()
init_api_session()

# Get our initial ISBN cache per the CLI arguments supplied.
q = paren('isbn:'+logic_join(g_arg_isbn_list,'OR'))
cache = get_isbn_cache(q)

# Make sure we actually have some books before proceeding.
if cache['total'] > 0:
    have_books = True
    # Updated that cache, adding suggested books by author & ddc derived from the initial list.
    get_suggested_by_ddc(cache)
    output_items(cache)
    download_covers(cache)

# We unconditionally print this info even if we have no books from the initial
# search.
print(f'Total API calls: {g_total_api_calls}')
print(f'Total books: {cache["total"]}')

# Print this information only if we have books from the initial search.
if have_books == True:
    print('Book metadata is in output.csv file.')
    print('Covers for each ISBN are in respective JPG files.')
    print('If a cover for an ISBN is unavailable, reason will be in respective .txt files.')
else:
    print("No books were found for that ISBN input. Please try other ISBN(s).")

# Exit zero if we have books, 1 if we don't.
exit(0 if have_books else 1)
