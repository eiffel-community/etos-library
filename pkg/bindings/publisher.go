// Copyright Axis Communications AB.
//
// For a full list of individual contributors, please see the commit history.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//	http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
package bindings

import (
	"C"
	"log/slog"
	"os"

	"github.com/eiffel-community/etos-library/pkg/stream"
)

var (
	Streamer  stream.Streamer
	Publisher stream.Publisher
	Consumer  stream.Consumer
)
var logger = slog.New(slog.NewTextHandler(os.Stdout, nil))

// Connect to the stream.
//
//export Connect
func Connect(connectionString, streamName *C.char) bool {
	if err := setupPublisher(C.GoString(connectionString), C.GoString(streamName)); err != nil {
		logger.Error("Failed to setup publisher", slog.Any("Error", err))
		return false
	}
	return true
}

// Publish a message to the stream.
//
//export Publish
func Publish(event, identifier, eventType, meta *C.char) bool {
	message := C.GoString(event)
	filter := stream.Filter{
		Identifier: C.GoString(identifier),
		Type:       C.GoString(eventType),
		Meta:       C.GoString(meta),
	}
	Publisher.Publish([]byte(message), filter)
	return true
}

// Close any active publisher, streamer and consumer.
//
//export Close
func Close() {
	if Publisher != nil {
		Publisher.Close()
	}
	if Streamer != nil {
		Streamer.Close()
	}
	if Consumer != nil {
		Consumer.Close()
	}
}

// setupPublisher sets up a publisher for the stream.
func setupPublisher(connectionString, streamName string) error {
	var err error
	if Streamer == nil {
		if err = setupStreamer(connectionString, streamName); err != nil {
			return err
		}
	}
	// TODO: This name
	Publisher, err = Streamer.Publisher("publisher-1")
	if err != nil {
		return err
	}
	if err = Publisher.Start(); err != nil {
		return err
	}
	return nil
}

// setupStreamer sets up a streamer for the stream.
func setupStreamer(connectionString, streamName string) error {
	var err error
	addresses := []string{connectionString}
	Streamer, err = stream.NewRabbitMQStreamer(streamName, addresses, logger)
	return err
}
