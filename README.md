# lightning thing

pulls from a websocket and puts dots on a map.

## how it broke

first try was just leaflet markers. browser died. too many dom elements. sucked.

second try was a canvas. kept all the dots in a js array. had to loop it every frame to fade them. still slow as hell when a real storm hit. js thread got clogged. dropped most of the data.

## how i fixed it

the array was the problem. managing state is slow.

read about some stateless rendering trick. a "phosphor screen" thing.

new dots just get drawn once. fire and forget. then the whole canvas just gets faded a little bit each frame. no more array. no more loops. the work is always the same no matter how many strikes.

now it handles the firehose. it works.

## run it/

1.  `pip install -r requirements.txt`
2.  `python app.py`
3.  go to localhost:5000
