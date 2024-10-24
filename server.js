const express = require('express');
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');
const socketIo = require('socket.io');
const cors = require('cors');
const fs = require('fs');

const app = express();
const server = http.createServer(app);
const io = socketIo(server, {
  cors: {
    origin: 'http://localhost:3000',
    methods: ['GET', 'POST']
  }
});

app.use(cors({
  origin: 'http://localhost:3000'
}));
app.use(express.json());

let isRunning = false;
let customizationData = {
  plotWidth: 3,
  plotHeightFactor: 3.15,
  dotSize: 1,
  colorMap: 'Reds'
};
let selectedDatasets = []

app.get('/get_dataset_images', (req, res) => {
  const selectedDatasetFile = req.query.dataset;
  console.log('Selected dataset file:', selectedDatasetFile); // Log selected dataset

  const datasetFilePath = path.join(__dirname, 'datasets', selectedDatasetFile);
  console.log('Dataset file path:', datasetFilePath); // Log dataset file path

  // Check if the dataset list file exists
  if (!fs.existsSync(datasetFilePath)) {
    return res.status(404).json({ error: 'Dataset list file not found' });
  }

  // Read the dataset list file to get the filenames
  fs.readFile(datasetFilePath, 'utf8', (err, data) => {
    if (err) {
      return res.status(500).json({ error: 'Failed to read dataset list file' });
    }

    // Split the list file contents by newlines to get the image filenames
    const imageFilenames = data.split('\n').filter(line => line.trim() !== ''); // Ignore empty lines

    // Construct URLs for these images (assuming they're located in the 'output_plots' directory)
    const imageUrls = imageFilenames.map(file => {
      if (!file.endsWith('.png')) {
        file += '.png'; // Add .png extension if missing
      }
      return `/output_plots/${file}`;
    });

    // Send the image URLs back to the frontend
    res.json(imageUrls);
  });
});


app.get('/get_dataset_images_2', (req, res) => {
  const selectedDatasetFile = req.query.dataset;
  console.log('Selected dataset file:', selectedDatasetFile); // Log selected dataset

  const datasetFilePath = path.join(__dirname, 'datasets', selectedDatasetFile);
  console.log('Dataset file path:', datasetFilePath); // Log dataset file path

  // Check if the dataset list file exists
  if (!fs.existsSync(datasetFilePath)) {
    return res.status(404).json({ error: 'Dataset list file not found' });
  }

  // Read the dataset list file to get the filenames
  fs.readFile(datasetFilePath, 'utf8', (err, data) => {
    if (err) {
      return res.status(500).json({ error: 'Failed to read dataset list file' });
    }

    // Split the list file contents by newlines to get the image filenames
    const imageFilenames = data.split('\n').filter(line => line.trim() !== ''); // Ignore empty lines

    // Ensure .png extension is added if missing
    const imageUrls = imageFilenames.map(file => {
      if (!file.endsWith('.png')) {
        file += '.png'; // Add .png extension if missing
      }
      return `/output_plots_2/${file}`; // Change to output_plots_2
    });

    // Send the image URLs back to the frontend
    res.json(imageUrls);
  });
});



app.post('/customize_plots', (req, res) => {
  // Store the customization data from the frontend
  customizationData = {
    cmap: req.body.colorMap || 'Reds',
    plotWidth: req.body.plotWidth || 3,
    dotSize: req.body.dotSize || 1,
    plotHeightFactor: req.body.plotHeightFactor || 3.15,
    dotSize2: req.body.dotSize2 || 1,
    outlineThickness: req.body.outlineThickness || 0.1,  // Default to 0.1

    //dotSize2: req.body.dotSize2 || 1,
    //outlineThickness: req.body.outlineThickness || 0.1,  // Default to 0.1
  };

  console.log('Received customization data:', customizationData);
  res.status(200).json({ message: 'Customization data saved successfully' });
});


app.get('/get_customization', (req, res) => {
  res.status(200).json(customizationData); // Send the saved customization settings
});


// Pass the customization to the Python script when starting the process
app.post('/start_processing', (req, res) => {
  const scriptPath = path.resolve(__dirname, 'diffexpr.py');
  

  console.log('Customization data sent to Python script:', customizationData);

  // Pass the stored customization data to the Python script
  const child = spawn('python3.9', ['-u', scriptPath, 'plot_results', 'gsm.list' , 'sample.query.list',  
    JSON.stringify(customizationData)]);

  child.stdout.on('data', (data) => {
    console.log(`stdout: ${data}`);
    io.emit('output', data.toString());
  });

  child.stderr.on('data', (data) => {
    console.error(`stderr: ${data}`);
  });

  child.on('close', (code) => {
    console.log(`Child process exited with code ${code}`);
    io.emit('processingComplete', { message: 'Processing complete' });
    res.status(200).json({ message: 'Processing complete' });
  });
});



app.post('/set_selected_datasets', (req, res) => {
  const { datasets } = req.body; // Get the selected dataset file names from the request body

  if (!datasets || datasets.length === 0) {
    return res.status(400).json({ error: 'No datasets selected' });
  }

  selectedDatasets = datasets; // Store the selected datasets
  console.log('Selected datasets received:', selectedDatasets);

  res.status(200).json({ message: 'Datasets received successfully' });
});


app.post('/search', (req, res) => {
  const { selectedDatasets, searchTerm } = req.body;

  if (!selectedDatasets || selectedDatasets.length === 0) {
    return res.status(400).json({ message: 'No datasets selected' });
  }

  if (isRunning) {
    return res.status(400).json({ message: 'Script is already running' });
  }

  isRunning = true;

  // Read and merge the dataset files into one file
  const combinedDatasetFilePath = path.join(__dirname, 'combined_datasets.list');
  const combinedDatasetStream = fs.createWriteStream(combinedDatasetFilePath);

  selectedDatasets.forEach((dataset) => {
    const datasetFilePath = path.join(__dirname, 'datasets', dataset);
    
    if (fs.existsSync(datasetFilePath)) {
      const fileContent = fs.readFileSync(datasetFilePath, 'utf8');
      combinedDatasetStream.write(fileContent + '\n'); // Write content to the combined file
    }
  });

  combinedDatasetStream.end(); // Close the stream after writing all content

  // After combining the dataset files, proceed with processing
  combinedDatasetStream.on('finish', () => {
    const queryFilePath = path.join(__dirname, 'sample.query.list');
    const queryContent = searchTerm.trim().split(/\s+/).join(' '); 
    fs.writeFileSync(queryFilePath, queryContent);

    const scriptPath = path.resolve(__dirname, 'diffexpr.py');
    const scriptPath2 = path.resolve(__dirname, 'generate_plots.py');

    // First child process
    const child = spawn('python3.9', ['-u', scriptPath, combinedDatasetFilePath, queryFilePath, 'output.png', 'output.gene.list.txt', 'output2.png']);

    child.stdout.on('data', (data) => {
      const output = data.toString();
      console.log(output);

      const progressMatch = output.match(/Progress: (\d+(\.\d+)?)%/);
      if (progressMatch) {
        const progress = parseFloat(progressMatch[1]);
        io.emit('progress', { progress });
      }
    
      io.emit('output', output);
    });

    child.stderr.on('data', (data) => {
      const error = data.toString();
      console.error(error);
      io.emit('output', error);
    });

    // When the first child finishes, start the second child process
    child.on('close', (code) => {
      console.log(`child process exited with code ${code}`);
      io.emit('output', `child process exited with code ${code}`);

      if (code === 0) { // Check if the first child exited successfully
        // Start second child process only after the first one finishes
        const child2 = spawn('python3.9', ['-u', scriptPath2, combinedDatasetFilePath, queryFilePath, 'output.gene.list.txt']);

        child2.stdout.on('data', (data) => {
          const output = data.toString();
          console.log(`child2: ${output}`);
          io.emit('output', `child2: ${output}`);
        });

        child2.stderr.on('data', (data) => {
          const error = data.toString();
          console.error(`child2 error: ${error}`);
          io.emit('output', `child2 error: ${error}`);
        });

        child2.on('close', (code) => {
          console.log(`child2 process exited with code ${code}`);
          io.emit('output', `child2 process exited with code ${code}`);
          generateImageLists(); // After both processes finish, generate the image lists.
          io.emit('processingComplete', { message: 'Processing complete. New data available.' });
          res.json({ message: 'Processing complete' });
        });
      } else {
        isRunning = false;
        res.status(500).json({ message: 'First process failed.' });
      }
    });
  });
});

// Serve static files (output.png and output.gene.list.txt)
app.use(express.static(__dirname));

app.use('/output_plots', express.static(path.join(__dirname, 'output_plots')));
app.use('/output_plots_2', express.static(path.join(__dirname, 'output_plots_2')));


function generateImageLists() {
  const outputPlotsDir = path.join(__dirname, 'output_plots');
  const outputPlots2Dir = path.join(__dirname, 'output_plots_2');

  fs.readdir(outputPlotsDir, (err, files) => {
    if (err) {
      console.error('Unable to scan directory: ' + err);
      return;
    }
    const images = files.filter(file => file.endsWith('.png'));
    fs.writeFileSync(path.join(__dirname, 'output_plots_list.txt'), images.join('\n'));
  });

  fs.readdir(outputPlots2Dir, (err, files) => {
    if (err) {
      console.error('Unable to scan directory: ' + err);
      return;
    }
    const images = files.filter(file => file.endsWith('.png'));
    fs.writeFileSync(path.join(__dirname, 'output_plots_2_list.txt'), images.join('\n'));
  });
}

io.on('connection', (socket) => {
  console.log('Client connected');
});

server.listen(3001, () => {
  console.log('Server is running on http://localhost:3001');
});


