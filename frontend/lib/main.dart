import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';
import 'dart:io';
import 'package:file_picker/file_picker.dart';

import 'Lessons.dart';
import 'Materials.dart';

void main() {
  runApp(MyApp());
}

Future<void> uploadPDF() async {
  FilePickerResult? result = await FilePicker.platform.pickFiles(
    type: FileType.custom,
    allowedExtensions: ['pdf'],
  );

  if (result != null) {
    File file = File(result.files.single.path!);
    var request = http.MultipartRequest(
      'POST',
      Uri.parse('http://10.0.2.2:5000/upload'),
    );

    request.files.add(await http.MultipartFile.fromPath('file', file.path));
    var response = await request.send();

    if (response.statusCode == 200) {
      print('File uploaded successfully');
    } else {
      print('Failed to upload file: ${response.statusCode}');
    }
  }
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => MyAppState(),
      child: MaterialApp(
        title: 'Text Uploader',
        theme: ThemeData(
          useMaterial3: true,
          colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepOrange),
        ),
        home: MyHomePage(),
      ),
    );
  }
}

class MyAppState extends ChangeNotifier {
  List<String> uploadedTexts = [];



  @override
  void notifyListeners() {
    super.notifyListeners();
  }
}

class MyHomePage extends StatefulWidget {
  @override
  State<MyHomePage> createState() => _MyHomePageState();
}

class _MyHomePageState extends State<MyHomePage> {
  var selectedIndex = 0;

  @override
  Widget build(BuildContext context) {
    Widget page;
    switch (selectedIndex) {
      case 0:
        page = UploadPage();
        break;
      case 1:
        page = FavouritesPage();
        break;
      case 2:
        page = Lessons();
        break;
      default:
        throw UnimplementedError('No widget for $selectedIndex');
    }

    return LayoutBuilder(
      builder: (context, constraints) {
        return Scaffold(
          body: Row(
            children: [
              SafeArea(
                child: NavigationRail(
                  extended: constraints.maxWidth >= 600,
                  destinations: [
                    NavigationRailDestination(
                      icon: Icon(Icons.upload),
                      label: Text('Upload'),
                    ),
                    NavigationRailDestination(
                      icon: Icon(Icons.list),
                      label: Text('Materials'),
                    ),
                    NavigationRailDestination(
                      icon: Icon(Icons.new_label), 
                      label: Text ('Lessons')
                      )
                  ],
                  selectedIndex: selectedIndex,
                  onDestinationSelected: (value) {
                    setState(() {
                      selectedIndex = value;
                    });
                  },
                ),
              ),
              Expanded(
                child: Container(
                  color: Theme.of(context).colorScheme.primaryContainer,
                  child: page,
                ),
              )
            ],
          ),
        );
      },
    );
  }
}


class UploadPage extends StatefulWidget {
  @override
  _UploadPageState createState() => _UploadPageState();
}

class _UploadPageState extends State<UploadPage> {
  bool _isUploading = false;

  Future<void> uploadPDF() async {
    FilePickerResult? result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf'],
    );

    if (result != null) {
      setState(() => _isUploading = true); // Show loading state

      File file = File(result.files.single.path!);
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('http://10.0.2.2:5000/upload'), // Flask API
      );

      request.files.add(await http.MultipartFile.fromPath('file', file.path));
      var response = await request.send();

      if (!mounted) return; // Prevents using context if widget is disposed

      setState(() => _isUploading = false); // Hide loading state

      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(response.statusCode == 200
              ? 'File uploaded successfully!'
              : 'Failed to upload file'),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Upload PDF')),
      body: Center(
        child: _isUploading
            ? CircularProgressIndicator() // Show loading spinner while uploading
            : ElevatedButton(
                onPressed: uploadPDF,
                child: Text("Upload PDF"),
              ),
      ),
    );
  }
}

Future<List<String>> fetchFiles() async {
  final url = Uri.parse('http://10.0.2.2:5000/get_files'); 
  try {
    final response = await http.get(url);
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return List<String>.from(data['files']);
    } else {
      throw Exception('Failed to load file names');
    }
  } catch (e) {
    print('Error fetching files: $e');
    return [];
  }
}



