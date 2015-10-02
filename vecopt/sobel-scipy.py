

from skimage import data, io, filter

image = data.coins() # or any NumPy array!
io.imshow(image)
io.show()
edges = filter.sobel(image)
io.imshow(edges)
io.show()


